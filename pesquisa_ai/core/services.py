import csv
import io
import os
import re
import math
import statistics
import uuid
from collections import Counter, defaultdict
from datetime import datetime

MAX_CATEGORIES = 25
MAX_ROWS = 20_000
QUASI_NUMERIC_RE = re.compile(r'[R$€£¥%\s_]')

_TIMESTAMP_FRAGMENTS = ['carimbo', 'timestamp', 'data/hora', 'data e hora', 'datetime', 'date', 'hora']
_CONSENT_FRAGMENTS = ['concorda', 'consent', 'aceito', 'concordo']

# ID/code column name patterns (whole word or common prefix/suffix)
_ID_NAME_PATTERNS = re.compile(
    r'(^|[\s_\-\.])('
    r'id|ids|cod|code|codes|codigo|códigos|codigos|chave|chaves|key|keys|'
    r'uuid|guid|hash|token|protocolo|numero|número|num|ref|referencia|referência|'
    r'registro|reg|cpf|cnpj|rg|matricula|matrícula|identificador'
    r')([\s_\-\.]|$)',
    re.IGNORECASE,
)
# Also matches if name IS exactly one of those tokens
_ID_NAME_EXACT = re.compile(
    r'^('
    r'id|ids|cod|code|codigo|chave|key|uuid|guid|hash|token|protocolo|'
    r'numero|num|ref|registro|reg|cpf|cnpj|rg|matricula|identificador'
    r')$',
    re.IGNORECASE,
)

# Year column name patterns
_YEAR_NAME_RE = re.compile(r'(^|[\s_\-\.])ano([\s_\-\.]|$)|(^|[\s_\-\.])year([\s_\-\.]|$)', re.IGNORECASE)
_YEAR_VALUE_RE = re.compile(r'^(19|20)\d{2}$')


def _is_consent(name):
    return any(x in name.lower() for x in _CONSENT_FRAGMENTS)


def _is_id_column(name, values):
    """Return True if this column looks like an ID / code column that should be skipped."""
    n = name.strip()
    if _ID_NAME_EXACT.match(n) or _ID_NAME_PATTERNS.search(n):
        return True
    # Heuristic (data-based): almost-unique pure integers → sequential ID
    # Only fires for integer-looking values — avoids false positives on scores, names, etc.
    if not values or len(values) < 5:
        return False
    unique_ratio = len(set(values)) / len(values)
    if unique_ratio > 0.95:
        sample = [str(v).strip() for v in values[:300]]
        all_integers = all(re.match(r'^-?\d{1,15}$', s) for s in sample)
        if all_integers:
            return True
    return False


def _is_year_column(name, values):
    """Return True if this column represents years (should be grouped, not statistically summarised)."""
    n = name.strip()
    if _YEAR_NAME_RE.search(n):
        return True
    if not values:
        return False
    # Check if values look like years (1900-2100) and few unique values
    sample = [str(v).strip() for v in values[:200]]
    year_like = [s for s in sample if _YEAR_VALUE_RE.match(s)]
    if len(year_like) / max(len(sample), 1) >= 0.85:
        all_vals = [str(v).strip() for v in values]
        year_vals = [int(v) for v in all_vals if _YEAR_VALUE_RE.match(v)]
        unique_years = len(set(year_vals))
        if unique_years <= 50:  # reasonable number of distinct years
            return True
    return False


def calc_year_distribution(values):
    """Group values by year and return a bar-chart-friendly summary."""
    str_vals = [str(v).strip() for v in values if _YEAR_VALUE_RE.match(str(v).strip())]
    freq = Counter(str_vals)
    ordered = sorted(freq.items())
    labels = [k for k, _ in ordered]
    counts = [v for _, v in ordered]
    total = len(str_vals)
    unique = len(freq)

    if not ordered:
        return None

    peak_year, peak_count = max(freq.items(), key=lambda x: x[1])
    peak_pct = round(peak_count / total * 100, 1) if total else 0
    insight = (
        f'{unique} anos distintos encontrados em {total} respostas. '
        f'Ano com mais respostas: {peak_year} ({peak_pct}%).'
    )

    return {
        'labels': labels,
        'values': counts,
        'total': total,
        'unique_count': unique,
        'chart_type': 'bar',
        'chart_options': ['bar', 'line'],
        'insight': insight,
    }


def _try_float(v):
    cleaned = QUASI_NUMERIC_RE.sub('', str(v).strip())
    cleaned = cleaned.replace(',', '.')
    parts = cleaned.split('.')
    if len(parts) > 2:
        cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _try_date(v):
    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%y', '%Y/%m/%d']:
        try:
            return datetime.strptime(str(v).strip(), fmt)
        except (ValueError, TypeError):
            pass
    return None


def _detect_csv_delimiter(text_sample):
    candidates = [',', ';', '\t', '|']
    counts = {d: text_sample.count(d) for d in candidates}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ','


def _decode_content(content):
    if content.startswith(b'\xff\xfe') or content.startswith(b'\xfe\xff'):
        try:
            return content.decode('utf-16')
        except Exception:
            pass
    if content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
    for enc in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-16']:
        try:
            return content.decode(enc)
        except (UnicodeDecodeError, Exception):
            continue
    return content.decode('utf-8', errors='replace')


def _detect_outliers(nums):
    if len(nums) < 4:
        return []
    sorted_nums = sorted(nums)
    n = len(sorted_nums)
    q1 = sorted_nums[n // 4]
    q3 = sorted_nums[(3 * n) // 4]
    iqr = q3 - q1
    if iqr == 0:
        return []
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return [v for v in nums if v < lower or v > upper]


def _smart_chart_type_numeric(n, nums):
    """Return best chart type and options for numeric data."""
    unique_ratio = len(set(nums)) / n if n > 0 else 1
    if n <= 20 and unique_ratio < 0.5:
        return 'bar', ['bar', 'pie', 'doughnut']
    return 'bar', ['bar', 'line']


def _smart_chart_type_categorical(unique_count):
    """Return best chart type and options based on unique category count."""
    if unique_count <= 4:
        return 'pie', ['pie', 'doughnut', 'bar']
    elif unique_count <= 8:
        return 'doughnut', ['doughnut', 'bar', 'pie']
    else:
        return 'bar', ['bar', 'doughnut']


def calc_numeric(nums):
    if not nums:
        return None
    n = len(nums)
    media = sum(nums) / n
    desvio = statistics.pstdev(nums)
    sorted_n = sorted(nums)
    mediana = statistics.median(nums)

    try:
        moda = statistics.multimode(nums)[:3]
    except Exception:
        moda = []

    q1 = sorted_n[n // 4]
    q3 = sorted_n[(3 * n) // 4]
    outliers = _detect_outliers(nums)

    if n > 1:
        mean_x = (n - 1) / 2
        mean_y = media
        num_slope = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(nums))
        den_slope = sum((i - mean_x) ** 2 for i in range(n))
        slope = num_slope / den_slope if den_slope != 0 else 0
        scale = abs(media) or 1
        if slope > 0.01 * scale:
            tendencia = 'crescimento'
        elif slope < -0.01 * scale:
            tendencia = 'queda'
        else:
            tendencia = 'estável'
    else:
        tendencia = 'estável'

    insights = []
    insights.append(f'Média {round(media, 2)}, mediana {round(mediana, 2)}, com tendência de {tendencia}.')
    if outliers:
        insights.append(f'{len(outliers)} outlier(s) detectado(s): {[round(o, 2) for o in outliers[:5]]}.')
    cv = (desvio / abs(media)) if media != 0 else 0
    if cv < 0.1:
        insights.append('Alta concentração: dados muito homogêneos.')
    elif cv > 0.5:
        insights.append('Alta dispersão: dados muito heterogêneos.')
    insights.append(f'80% dos valores estão entre {round(q1, 2)} e {round(q3, 2)}.')

    if n > 1 and max(nums) != min(nums):
        bin_count = min(10, max(5, int(math.sqrt(n))))
        bin_width = (max(nums) - min(nums)) / bin_count
        bins = defaultdict(int)
        for v in nums:
            b = int((v - min(nums)) / bin_width)
            if b == bin_count:
                b -= 1
            bins[b] += 1
        hist_labels = [
            f'{round(min(nums) + i * bin_width, 2)}-{round(min(nums) + (i+1) * bin_width, 2)}'
            for i in range(bin_count)
        ]
        hist_values = [bins.get(i, 0) for i in range(bin_count)]
    else:
        hist_labels = [str(nums[0])]
        hist_values = [1]

    recommended, chart_options = _smart_chart_type_numeric(n, nums)

    return {
        'media': round(media, 2),
        'mediana': round(mediana, 2),
        'moda': [round(m, 2) if isinstance(m, float) else m for m in moda],
        'min': round(min(nums), 2),
        'max': round(max(nums), 2),
        'desvio_padrao': round(desvio, 2),
        'q1': round(q1, 2),
        'q3': round(q3, 2),
        'total': round(sum(nums), 2),
        'count': n,
        'outliers': [round(o, 2) for o in outliers[:20]],
        'outlier_count': len(outliers),
        'tendencia': tendencia,
        'insight': ' '.join(insights),
        'chart_type': recommended,
        'chart_options': chart_options,
        'hist_labels': hist_labels,
        'hist_values': hist_values,
    }


def calc_categorical(values):
    freq = Counter(values)
    total = len(values)
    top = freq.most_common(MAX_CATEGORIES)
    labels = [k for k, _ in top]
    vals = [v for _, v in top]

    unique_count = len(freq)
    recommended, chart_options = _smart_chart_type_categorical(unique_count)

    dominant_pct = round(vals[0] / total * 100, 1) if vals else 0
    insights = [f'Categoria dominante: \u201c{labels[0]}\u201d com {dominant_pct}% das respostas.']
    if len(labels) >= 2:
        second_pct = round(vals[1] / total * 100, 1)
        insights.append(f'Segunda mais frequente: \u201c{labels[1]}\u201d com {second_pct}%.')
    insights.append(f'{unique_count} categorias únicas entre {total} respostas.')

    return {
        'labels': labels,
        'values': vals,
        'total': total,
        'unique_count': unique_count,
        'chart_type': recommended,
        'chart_options': chart_options,
        'insight': ' '.join(insights),
    }


def calc_categorical_stats(values):
    return calc_categorical(values)


def calc_temporal(dates):
    freq = Counter([d.strftime('%Y-%m') for d in dates])
    ordered = sorted(freq.items())
    values = [v for _, v in ordered]

    if len(values) > 1:
        trend = 'crescimento' if values[-1] > values[0] else ('queda' if values[-1] < values[0] else 'estável')
    else:
        trend = 'estável'

    peak_month = max(freq, key=freq.get)
    try:
        peak_dt = datetime.strptime(peak_month, '%Y-%m')
        meses_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        peak_label = meses_pt[peak_dt.month - 1] + '/' + str(peak_dt.year)
    except Exception:
        peak_label = peak_month

    return {
        'labels': [k for k, _ in ordered],
        'values': values,
        'total': len(dates),
        'chart_type': 'line',
        'chart_options': ['line', 'bar'],
        'tendencia': trend,
        'insight': f'Evolução ao longo do tempo com tendência de {trend}. Pico em {peak_label}.',
    }


def detect_type(values):
    clean = [str(v).strip() for v in values if str(v).strip()]
    if not clean:
        return 'text', clean

    nums = [_try_float(v) for v in clean]
    valid_nums = [v for v in nums if v is not None]
    if len(valid_nums) / len(clean) >= 0.7:
        return 'numeric', valid_nums

    dates = [_try_date(v) for v in clean]
    valid_dates = [d for d in dates if d is not None]
    if len(valid_dates) / len(clean) >= 0.7:
        return 'temporal', valid_dates

    unique_ratio = len(set(clean)) / len(clean)
    if unique_ratio < 0.6 or len(set(clean)) <= 20:
        return 'categorical', clean

    return 'text', clean


def calc_correlation(col_a_vals, col_b_vals):
    n = min(len(col_a_vals), len(col_b_vals))
    if n < 3:
        return None
    a = col_a_vals[:n]
    b = col_b_vals[:n]
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    num = sum((ai - mean_a) * (bi - mean_b) for ai, bi in zip(a, b))
    den_a = math.sqrt(sum((ai - mean_a) ** 2 for ai in a))
    den_b = math.sqrt(sum((bi - mean_b) ** 2 for bi in b))
    if den_a == 0 or den_b == 0:
        return None
    return round(num / (den_a * den_b), 3)


def build_correlations(columns):
    numeric_cols = [c for c in columns if c.get('type') == 'numeric']
    if len(numeric_cols) < 2:
        return []
    correlations = []
    for i, col_a in enumerate(numeric_cols):
        for j, col_b in enumerate(numeric_cols):
            if j <= i:
                continue
            vals_a = col_a.get('raw_values', [])
            vals_b = col_b.get('raw_values', [])
            r = calc_correlation(vals_a, vals_b)
            if r is None:
                continue
            abs_r = abs(r)
            strength = 'forte' if abs_r >= 0.7 else ('moderada' if abs_r >= 0.4 else 'fraca')
            direction = 'positiva' if r >= 0 else 'negativa'
            correlations.append({
                'col_a': col_a['name'],
                'col_b': col_b['name'],
                'r': r,
                'abs_r': abs_r,
                'strength': strength,
                'direction': direction,
                'insight': f'Correlação {strength} {direction} entre \u201c{col_a["name"]}\u201d e \u201c{col_b["name"]}\u201d (r={r}).',
            })
    correlations.sort(key=lambda x: -x['abs_r'])
    return correlations[:10]


def parse_csv_as_analysis(content, source_name=''):
    try:
        text = _decode_content(content)
    except Exception as e:
        return None, f'Erro ao decodificar arquivo: {e}'

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return None, 'Arquivo vazio ou sem dados legíveis.'
    if len(lines) < 2:
        return None, 'CSV precisa ter pelo menos um cabeçalho e uma linha de dados.'

    sample = '\n'.join(lines[:5])
    delimiter = _detect_csv_delimiter(sample)

    # Enforce row limit — keep header + up to MAX_ROWS data lines
    total_data_lines = len(lines) - 1  # exclude header
    was_truncated = total_data_lines > MAX_ROWS
    if was_truncated:
        lines = [lines[0]] + lines[1:MAX_ROWS + 1]

    cleaned_text = '\n'.join(lines)

    try:
        reader = csv.DictReader(io.StringIO(cleaned_text), delimiter=delimiter)
        all_rows = list(reader)
    except Exception as e:
        return None, f'Erro ao ler CSV: {e}'

    if not all_rows:
        return None, 'CSV não contém dados após o cabeçalho.'

    all_rows = [r for r in all_rows if any(str(v).strip() for v in r.values())]

    columns_raw = defaultdict(list)
    for row in all_rows:
        for k, v in row.items():
            if k:
                columns_raw[k.strip()].append(str(v).strip() if v else '')

    columns = []
    skipped_ids = []
    for col_name, raw_vals in columns_raw.items():
        if not col_name:
            continue

        if _is_consent(col_name):
            col = {
                'name': col_name,
                'type': 'consent',
                'total': len(raw_vals),
                'consent_message': f'Coluna de consentimento — {len(raw_vals)} resposta(s).',
            }
            columns.append(col)
            continue

        non_empty = [v for v in raw_vals if v and v.lower() not in ('', 'n/a', 'null', 'none', '-')]
        if not non_empty:
            continue

        # Skip ID/code columns — not meaningful for analysis
        if _is_id_column(col_name, non_empty):
            skipped_ids.append(col_name)
            continue

        # Year columns: group by year instead of computing numeric stats
        if _is_year_column(col_name, non_empty):
            year_stats = calc_year_distribution(non_empty)
            if year_stats:
                col = {
                    'name': col_name,
                    'type': 'year',
                    'total': len(raw_vals),
                    'stats': year_stats,
                }
                columns.append(col)
            continue

        tipo, parsed = detect_type(non_empty)
        col = {'name': col_name, 'type': tipo, 'total': len(raw_vals)}

        if tipo == 'numeric':
            col['stats'] = calc_numeric(parsed)
            col['raw_values'] = parsed[:500]
        elif tipo == 'categorical':
            col['stats'] = calc_categorical(parsed)
        elif tipo == 'temporal':
            col['stats'] = calc_temporal(parsed)
        elif tipo == 'text':
            col['sample'] = list(set(parsed))[:5]
            col['total_unique'] = len(set(parsed))

        columns.append(col)

    if not columns:
        return None, 'Nenhuma coluna com dados válidos encontrada.'

    correlations = build_correlations(columns)

    for col in columns:
        col.pop('raw_values', None)

    global_insights = []
    numeric_cols = [c for c in columns if c.get('type') == 'numeric']
    cat_cols = [c for c in columns if c.get('type') == 'categorical']
    if numeric_cols:
        global_insights.append(f'{len(numeric_cols)} coluna(s) numérica(s) detectada(s).')
    if cat_cols:
        global_insights.append(f'{len(cat_cols)} coluna(s) categórica(s) detectada(s).')
    if correlations:
        top = correlations[0]
        global_insights.append(f'Correlação mais forte: {top["insight"]}')

    result = {
        'source_name': source_name,
        'type': 'csv',
        'total_responses': len(all_rows),
        'columns': columns,
        'correlations': correlations,
        'global_insights': global_insights,
        'share_token': str(uuid.uuid4())[:8],
        'was_truncated': was_truncated,
        'original_row_count': total_data_lines,
        'skipped_id_columns': skipped_ids,
    }
    return result, None


def build_analysis_from_form(formulario):
    from .models import ItemResposta

    columns = []
    numeric_col_data = {}

    for p in formulario.perguntas.all():
        valores = list(
            ItemResposta.objects.filter(pergunta_id=p.pergunta_id)
            .values_list('valor', flat=True)
        )
        if not valores:
            continue

        tipo, parsed = detect_type(valores)
        col = {'name': p.texto, 'type': tipo, 'total': len(valores)}

        if tipo == 'numeric':
            col['stats'] = calc_numeric(parsed)
            numeric_col_data[p.texto] = parsed
        elif tipo == 'categorical':
            col['stats'] = calc_categorical(parsed)
        elif tipo == 'temporal':
            col['stats'] = calc_temporal(parsed)

        columns.append(col)

    for col in columns:
        if col['type'] == 'numeric' and col['name'] in numeric_col_data:
            col['raw_values'] = numeric_col_data[col['name']]

    correlations = build_correlations(columns)

    for col in columns:
        col.pop('raw_values', None)

    return {
        'source_name': formulario.titulo,
        'type': 'form',
        'total_responses': formulario.respostas.count(),
        'columns': columns,
        'correlations': correlations,
        'global_insights': [],
        'share_token': str(uuid.uuid4())[:8],
    }


def generate_column_insight(col):
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return None, 'GROQ_API_KEY não configurada.'

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        s = col.get('stats') or {}
        col_type = col.get('type', '')
        name = col.get('name', 'coluna')

        if col_type == 'numeric':
            ctx = (
                f'Coluna numérica: "{name}"\n'
                f'Média: {s.get("media")}, Mediana: {s.get("mediana")}, '
                f'Min: {s.get("min")}, Max: {s.get("max")}\n'
                f'Desvio padrão: {s.get("desvio_padrao")}, Q1: {s.get("q1")}, Q3: {s.get("q3")}\n'
                f'Outliers: {s.get("outlier_count", 0)}, Tendência: {s.get("tendencia")}\n'
            )
        elif col_type == 'categorical':
            labels = s.get('labels', [])[:6]
            values = s.get('values', [])[:6]
            top = ', '.join(f'{l} ({v})' for l, v in zip(labels, values))
            ctx = (
                f'Coluna categórica: "{name}"\n'
                f'Categorias principais: {top}\n'
                f'Total de categorias únicas: {s.get("unique_count", len(labels))}\n'
                f'Insight automático: {s.get("insight", "")}\n'
            )
        else:
            ctx = f'Coluna "{name}" (tipo: {col_type}). Insight: {s.get("insight", "")}'

        r = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[
                {'role': 'system', 'content': (
                    'Você é um analista de dados especialista. '
                    'Gere um insight claro e útil em português sobre esta coluna de dados de pesquisa. '
                    'Seja específico, use os números disponíveis, e sugira uma conclusão prática. '
                    'Máximo 3 frases.'
                )},
                {'role': 'user', 'content': ctx[:3000]},
            ],
            temperature=0.4,
            max_tokens=250,
        )
        return r.choices[0].message.content.strip(), None
    except Exception as e:
        return None, str(e)


def generate_ai_response(question, context_data=None):
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return None, 'GROQ_API_KEY não configurada.'

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        context_str = ''
        if context_data and isinstance(context_data, dict):
            cols = context_data.get('columns', [])
            context_str = f'Fonte: {context_data.get("source_name", "dados")}, {context_data.get("total_responses", 0)} respostas.\n'
            for col in cols[:10]:
                context_str += f'- {col["name"]} ({col["type"]}): '
                if col.get('stats'):
                    st = col['stats']
                    if col['type'] == 'numeric':
                        context_str += f'média={st.get("media")}, min={st.get("min")}, max={st.get("max")}, outliers={st.get("outlier_count", 0)}'
                    elif col['type'] == 'categorical':
                        context_str += f'top={st.get("labels", [])[:3]}, insight={st.get("insight", "")}'
                context_str += '\n'
            corr = context_data.get('correlations', [])
            if corr:
                context_str += 'Correlações:\n'
                for c in corr[:3]:
                    context_str += f'  {c["insight"]}\n'

        r = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[
                {'role': 'system', 'content': (
                    'Você é um analista de dados especialista. Responda em português, de forma clara e objetiva. '
                    'Forneça insights específicos com números quando disponíveis. Seja direto e útil.'
                )},
                {'role': 'user', 'content': (context_str + '\n\nPergunta: ' + question)[:4000]},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        return r.choices[0].message.content, None
    except Exception as e:
        return None, str(e)


def generate_global_insight(analysis_data):
    """Generate a comprehensive AI insight for the entire dataset."""
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return None, 'GROQ_API_KEY não configurada.'

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        cols = analysis_data.get('columns', [])
        total = analysis_data.get('total_responses', 0)
        source = analysis_data.get('source_name', 'dados')
        corrs = analysis_data.get('correlations', [])

        ctx = f'Análise de "{source}" com {total} respostas e {len(cols)} colunas.\n\n'

        numeric_cols = [c for c in cols if c.get('type') == 'numeric']
        cat_cols = [c for c in cols if c.get('type') == 'categorical']

        if numeric_cols:
            ctx += 'VARIÁVEIS NUMÉRICAS:\n'
            for c in numeric_cols[:8]:
                s = c.get('stats', {})
                ctx += (
                    f'- {c["name"]}: média={s.get("media")}, mediana={s.get("mediana")}, '
                    f'desvio={s.get("desvio_padrao")}, min={s.get("min")}, max={s.get("max")}, '
                    f'outliers={s.get("outlier_count", 0)}, tendência={s.get("tendencia")}\n'
                )

        if cat_cols:
            ctx += '\nVARIÁVEIS CATEGÓRICAS:\n'
            for c in cat_cols[:6]:
                s = c.get('stats', {})
                labels = s.get('labels', [])[:4]
                values = s.get('values', [])[:4]
                top = ', '.join(f'{l}({v})' for l, v in zip(labels, values))
                ctx += f'- {c["name"]}: top={top}, total_categorias={s.get("unique_count")}\n'

        if corrs:
            ctx += '\nCORRELAÇÕES SIGNIFICATIVAS:\n'
            for c in corrs[:5]:
                ctx += f'- {c["col_a"]} × {c["col_b"]}: r={c["r"]} ({c["strength"]} {c["direction"]})\n'

        r = client.chat.completions.create(
            model='llama-3.1-8b-instant',
            messages=[
                {'role': 'system', 'content': (
                    'Você é um analista de dados sênior. Analise o conjunto de dados fornecido e gere um relatório '
                    'executivo em português com: 1) Resumo geral dos dados, 2) Principais descobertas e padrões, '
                    '3) Anomalias ou pontos de atenção, 4) Recomendações práticas. '
                    'Use tópicos com bullet points (•). Seja específico, cite números. Máximo 400 palavras.'
                )},
                {'role': 'user', 'content': ctx[:5000]},
            ],
            temperature=0.35,
            max_tokens=800,
        )
        return r.choices[0].message.content.strip(), None
    except Exception as e:
        return None, str(e)
