import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import (
    Formulario, ItemResposta, OpcaoPergunta,
    Pergunta, RespostaFormulario, SavedAnalysis,
)
from django.core.exceptions import RequestDataTooBig

from .services import (
    calc_numeric,
    calc_categorical,
    calc_categorical_stats,
    generate_ai_response,
    generate_column_insight,
    generate_global_insight,
    parse_csv_as_analysis,
    build_analysis_from_form,
)

logger = logging.getLogger(__name__)


# ── Session helpers ─────────────────────────────────────────────────────────

def get_active_analysis(request):
    """Always returns a dict or None."""
    active = request.session.get("active_analysis")
    if active is None:
        return None
    if isinstance(active, str):
        try:
            active = json.loads(active)
            request.session["active_analysis"] = active
        except Exception:
            request.session.pop("active_analysis", None)
            return None
    if not isinstance(active, dict):
        request.session.pop("active_analysis", None)
        return None
    return active


def set_active_analysis(request, analysis):
    """Always store as dict."""
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except Exception:
            return
    request.session["active_analysis"] = analysis
    request.session.modified = True


def clear_active_analysis(request):
    request.session.pop("active_analysis", None)
    request.session.modified = True


# ── Page views ──────────────────────────────────────────────────────────────

def dashboard(request):
    active = get_active_analysis(request)
    return render(request, "dashboard.html", {
        "active_page": "dashboard",
        "active_analysis": active,
    })


def pesquisa(request):
    active = get_active_analysis(request)
    saved_list = [a.to_summary() for a in SavedAnalysis.objects.all()]
    forms_list = [f.to_dict() for f in Formulario.objects.prefetch_related("perguntas__opcoes", "respostas")]
    return render(request, "pesquisa.html", {
        "active_page": "pesquisa",
        "active_analysis": active,
        "saved_analyses": saved_list,
        "formularios": forms_list,
    })


def ia_page(request):
    active = get_active_analysis(request)
    return render(request, "ia.html", {
        "active_page": "ia",
        "active_analysis": active,
    })


# ── CSV upload ───────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_csv_upload(request):
    try:
        files = request.FILES
    except RequestDataTooBig:
        return JsonResponse({"error": "Arquivo muito grande. Máximo 50 MB."}, status=413)

    active = get_active_analysis(request)
    if active:
        return JsonResponse(
            {"error": "Existe uma análise ativa. Salve ou descarte antes de carregar um novo CSV."},
            status=409,
        )

    # Accept both field names for compatibility
    arquivo = request.FILES.get("arquivo") or request.FILES.get("file")
    if not arquivo:
        return JsonResponse({"error": "Nenhum arquivo enviado."}, status=400)
    if arquivo.size == 0:
        return JsonResponse({"error": "Arquivo vazio."}, status=400)
    if arquivo.size > 50 * 1024 * 1024:
        return JsonResponse({"error": "Arquivo muito grande. Máximo 50 MB."}, status=413)

    try:
        content = arquivo.read()
    except Exception as e:
        return JsonResponse({"error": f"Erro ao ler arquivo: {e}"}, status=400)

    analysis, error = parse_csv_as_analysis(content, source_name=arquivo.name)
    if error:
        return JsonResponse({"error": error}, status=400)

    set_active_analysis(request, analysis)
    response = {
        "ok": True,
        "source_name": analysis["source_name"],
        "column_count": len(analysis["columns"]),
        "total_responses": analysis["total_responses"],
        "correlations_count": len(analysis.get("correlations", [])),
        "was_truncated": analysis.get("was_truncated", False),
        "original_row_count": analysis.get("original_row_count", analysis["total_responses"]),
    }
    return JsonResponse(response)


# ── Analysis state management ────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_analysis_save(request):
    active = get_active_analysis(request)
    if not active:
        return JsonResponse({"error": "Nenhuma análise ativa para salvar."}, status=400)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)

    name = body.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "Nome é obrigatório."}, status=400)

    notes = body.get("notes", "").strip()

    saved = SavedAnalysis.objects.create(
        name=name,
        notes=notes,
        source_type=active.get("type", "csv"),
        source_name=active.get("source_name", ""),
        data=active,
    )

    clear_active_analysis(request)
    return JsonResponse({"ok": True, "id": saved.pk, "name": saved.name})


@csrf_exempt
@require_http_methods(["POST"])
def api_analysis_discard(request):
    clear_active_analysis(request)
    return JsonResponse({"ok": True})


@csrf_exempt
def api_analysis_open(request, analysis_id):
    active = get_active_analysis(request)
    if active:
        return JsonResponse(
            {"error": "Existe uma análise ativa. Salve ou descarte antes de abrir outra."},
            status=409,
        )
    try:
        saved = SavedAnalysis.objects.get(pk=analysis_id)
    except SavedAnalysis.DoesNotExist:
        return JsonResponse({"error": "Análise não encontrada."}, status=404)

    set_active_analysis(request, saved.data)
    return JsonResponse({"ok": True})


@csrf_exempt
def api_analysis_delete(request, analysis_id):
    if request.method != "DELETE":
        return JsonResponse({"error": "Método não suportado."}, status=405)
    try:
        saved = SavedAnalysis.objects.get(pk=analysis_id)
        saved.delete()
        return JsonResponse({"ok": True})
    except SavedAnalysis.DoesNotExist:
        return JsonResponse({"error": "Análise não encontrada."}, status=404)


def api_analyses_list(request):
    analyses = [a.to_summary() for a in SavedAnalysis.objects.all()]
    return JsonResponse({"analyses": analyses})


# ── Form management ─────────────────────────────────────────────────────────

@csrf_exempt
def api_form_create(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método não suportado."}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)

    titulo = body.get("titulo", "").strip()
    if not titulo:
        return JsonResponse({"error": "Título é obrigatório."}, status=400)

    perguntas_data = body.get("perguntas", [])
    if not perguntas_data:
        return JsonResponse({"error": "Adicione ao menos uma pergunta."}, status=400)

    for p in perguntas_data:
        if not p.get("texto", "").strip():
            return JsonResponse({"error": "Todas as perguntas precisam de texto."}, status=400)
        if p.get("tipo") == "multipla_escolha":
            opcoes = p.get("opcoes", [])
            if len(opcoes) < 2:
                return JsonResponse({"error": "Múltipla escolha precisa de ao menos 2 opções."}, status=400)
            for op in opcoes:
                if not op.get("texto", "").strip():
                    return JsonResponse({"error": "Todas as opções precisam ter texto."}, status=400)

    formulario = Formulario.objects.create(
        titulo=titulo,
        descricao=body.get("descricao", ""),
    )

    for i, p_data in enumerate(perguntas_data):
        pergunta = Pergunta.objects.create(
            formulario=formulario,
            pergunta_id=p_data.get("id", f"p{i}"),
            texto=p_data["texto"],
            tipo=p_data.get("tipo", "numerica"),
            principal=p_data.get("principal", False),
            ordem=i,
        )
        if p_data.get("tipo") == "multipla_escolha":
            for op in p_data.get("opcoes", []):
                OpcaoPergunta.objects.create(pergunta=pergunta, texto=op["texto"])

    return JsonResponse({"ok": True, "id": formulario.pk, "titulo": formulario.titulo})


@csrf_exempt
@require_http_methods(["POST"])
def api_form_respond(request, form_id):
    try:
        formulario = Formulario.objects.prefetch_related("perguntas").get(pk=form_id)
    except Formulario.DoesNotExist:
        return JsonResponse({"error": "Formulário não encontrado."}, status=404)

    try:
        body = json.loads(request.body)
        respostas_data = body.get("respostas", [])
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)

    if not respostas_data:
        return JsonResponse({"error": "Nenhuma resposta fornecida."}, status=400)

    resposta = RespostaFormulario.objects.create(formulario=formulario)
    for item in respostas_data:
        ItemResposta.objects.create(
            resposta=resposta,
            pergunta_id=item.get("pergunta_id", ""),
            valor=str(item.get("valor", "")),
        )

    return JsonResponse({
        "ok": True,
        "mensagem": "Respostas registradas com sucesso!",
        "total_respostas": formulario.respostas.count(),
    })


@csrf_exempt
@require_http_methods(["POST"])
def api_form_open_as_analysis(request, form_id):
    active = get_active_analysis(request)
    if active:
        return JsonResponse(
            {"error": "Existe uma análise ativa. Salve ou descarte antes de abrir outra."},
            status=409,
        )

    try:
        formulario = Formulario.objects.prefetch_related("perguntas__opcoes").get(pk=form_id)
    except Formulario.DoesNotExist:
        return JsonResponse({"error": "Formulário não encontrado."}, status=404)

    if formulario.respostas.count() == 0:
        return JsonResponse({"error": "Este formulário ainda não tem respostas."}, status=400)

    analysis = build_analysis_from_form(formulario)
    set_active_analysis(request, analysis)
    return JsonResponse({"ok": True})


@csrf_exempt
def api_form_delete(request, form_id):
    if request.method != "DELETE":
        return JsonResponse({"error": "Método não suportado."}, status=405)
    try:
        f = Formulario.objects.get(pk=form_id)
        f.delete()
        return JsonResponse({"ok": True})
    except Formulario.DoesNotExist:
        return JsonResponse({"error": "Formulário não encontrado."}, status=404)


# ── Ad-hoc data analysis ────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_data_analyze(request):
    try:
        body = json.loads(request.body)
        tipo = body.get("tipo", "numerico")
        dados = body.get("dados", [])
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)

    if not dados:
        return JsonResponse({"error": "Nenhum dado fornecido."}, status=400)
    if len(dados) > 10000:
        return JsonResponse({"error": "Máximo de 10.000 itens."}, status=400)

    if tipo == "numerico":
        from .services import _try_float
        numeros = [_try_float(str(v)) for v in dados]
        numeros = [v for v in numeros if v is not None]
        if not numeros:
            return JsonResponse({"error": "Nenhum número válido encontrado."}, status=400)
        result = calc_numeric(numeros)
        result["tipo"] = "numerico"
        result["valores"] = numeros[:200]
        return JsonResponse(result)

    elif tipo == "categorico":
        itens = [str(v).strip() for v in dados if str(v).strip()]
        if not itens:
            return JsonResponse({"error": "Nenhum valor categórico encontrado."}, status=400)
        stats = calc_categorical_stats(itens)
        stats["tipo"] = "categorico"
        return JsonResponse(stats)

    elif tipo == "data":
        from datetime import datetime
        from collections import Counter as C
        formatos = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%y", "%Y/%m/%d"]
        dias_semana_pt = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        meses_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

        datas = []
        invalidas = 0
        for v in dados:
            v = str(v).strip()
            if not v:
                continue
            parsed = None
            for fmt in formatos:
                try:
                    parsed = datetime.strptime(v, fmt)
                    break
                except ValueError:
                    pass
            if parsed:
                datas.append(parsed)
            else:
                invalidas += 1

        if not datas:
            return JsonResponse(
                {"error": "Nenhuma data válida. Use formatos como DD/MM/AAAA ou AAAA-MM-DD."},
                status=400,
            )

        datas.sort()
        total = len(datas)
        periodo = (datas[-1] - datas[0]).days
        por_mes_raw = C(d.strftime("%Y-%m") for d in datas)
        por_dia_raw = C(dias_semana_pt[d.weekday()] for d in datas)
        por_ano_raw = C(d.year for d in datas)
        mes_mais_comum_key = max(por_mes_raw, key=por_mes_raw.get)
        mes_mais_comum_dt = datetime.strptime(mes_mais_comum_key, "%Y-%m")
        mes_mais_comum_label = meses_pt[mes_mais_comum_dt.month - 1] + "/" + str(mes_mais_comum_dt.year)

        return JsonResponse({
            "tipo": "data",
            "total": total,
            "invalidas": invalidas,
            "data_inicio": datas[0].strftime("%d/%m/%Y"),
            "data_fim": datas[-1].strftime("%d/%m/%Y"),
            "periodo_dias": periodo,
            "mes_mais_comum": mes_mais_comum_label,
            "dia_mais_comum": max(por_dia_raw, key=por_dia_raw.get),
            "por_mes": [
                {"label": meses_pt[datetime.strptime(k, "%Y-%m").month - 1] + "/" + k[:4], "count": v}
                for k, v in sorted(por_mes_raw.items())
            ],
            "por_dia_semana": [{"label": d, "count": por_dia_raw.get(d, 0)} for d in dias_semana_pt],
            "por_ano": [{"label": str(k), "count": v} for k, v in sorted(por_ano_raw.items())],
            "insight": (
                f"Analisadas {total} datas ao longo de {periodo} dias. "
                f"Mês mais frequente: {mes_mais_comum_label}. "
                f"Dia da semana mais comum: {max(por_dia_raw, key=por_dia_raw.get)}."
            ),
        })

    return JsonResponse({"error": "Tipo inválido. Use: numerico, categorico, data."}, status=400)


# ── AI chat ──────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_ai_chat(request):
    try:
        body = json.loads(request.body)
        pergunta = body.get("pergunta", "").strip()
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)

    if not pergunta:
        return JsonResponse({"error": "Pergunta é obrigatória."}, status=400)

    active = get_active_analysis(request)
    resposta, erro = generate_ai_response(pergunta, context_data=active)

    if not resposta:
        if active:
            cols = active.get("columns", [])
            num_cols = [c for c in cols if c.get("type") == "numeric"]
            if num_cols:
                st = num_cols[0].get("stats", {})
                media = st.get("media", 0) or 1
                desvio = st.get("desvio_padrao", 0) or 0
                cv = desvio / abs(media) if media else 0
                if cv < 0.1:
                    resposta = "Os dados estão muito concentrados, indicando alta consistência."
                elif cv < 0.3:
                    resposta = f"Os dados apresentam dispersão moderada. Média: {st.get('media')}, desvio: {st.get('desvio_padrao')}."
                else:
                    resposta = f"Os dados possuem alta variabilidade. Amplitude: {(st.get('max', 0) or 0) - (st.get('min', 0) or 0):.2f}."
            else:
                resposta = "Carregue dados numéricos para análises estatísticas detalhadas."
        else:
            resposta = "Carregue um CSV ou abra uma análise salva para que a IA tenha contexto para responder."

    return JsonResponse({"resposta": resposta})


# ── AI column insight ─────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_column_insight(request):
    """Generate AI insight for a specific column by index from the active analysis."""
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)

    col_index = body.get("col_index")
    if col_index is None:
        return JsonResponse({"error": "col_index é obrigatório."}, status=400)

    active = get_active_analysis(request)
    if not active:
        return JsonResponse({"error": "Nenhuma análise ativa."}, status=400)

    cols = active.get("columns", [])
    try:
        col = cols[int(col_index)]
    except (IndexError, TypeError, ValueError):
        return JsonResponse({"error": "Coluna não encontrada."}, status=404)

    insight, erro = generate_column_insight(col)
    if not insight:
        return JsonResponse({"error": erro or "Erro ao gerar insight."}, status=500)

    return JsonResponse({"insight": insight})


# ── AI global insight ─────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_global_insight(request):
    """Generate a comprehensive AI insight for the entire active analysis."""
    active = get_active_analysis(request)
    if not active:
        return JsonResponse({"error": "Nenhuma análise ativa."}, status=400)

    insight, erro = generate_global_insight(active)
    if not insight:
        return JsonResponse({"error": erro or "Erro ao gerar insight global."}, status=500)

    return JsonResponse({"insight": insight})
