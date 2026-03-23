from django.db import models


class Formulario(models.Model):
    titulo = models.CharField(max_length=300)
    descricao = models.TextField(blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo

    def to_dict(self):
        perguntas = []
        for p in self.perguntas.order_by('ordem'):
            p_dict = {
                'id': p.pergunta_id,
                'texto': p.texto,
                'tipo': p.tipo,
                'principal': p.principal,
            }
            if p.tipo == 'multipla_escolha':
                p_dict['opcoes'] = [{'texto': op.texto} for op in p.opcoes.all()]
            perguntas.append(p_dict)
        return {
            'id': self.pk,
            'titulo': self.titulo,
            'descricao': self.descricao,
            'perguntas': perguntas,
            'total_respostas': self.respostas.count(),
            'criado_em': self.criado_em.strftime('%d/%m/%Y'),
        }

    class Meta:
        verbose_name = 'Formulário'
        verbose_name_plural = 'Formulários'
        ordering = ['-criado_em']


class Pergunta(models.Model):
    TIPOS = [
        ('numerica', 'Numérica'),
        ('multipla_escolha', 'Múltipla Escolha'),
        ('texto', 'Texto Livre'),
    ]
    formulario = models.ForeignKey(
        Formulario, on_delete=models.CASCADE, related_name='perguntas'
    )
    pergunta_id = models.CharField(max_length=100)
    texto = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS)
    principal = models.BooleanField(default=False)
    ordem = models.IntegerField(default=0)

    def __str__(self):
        return self.texto

    class Meta:
        verbose_name = 'Pergunta'
        verbose_name_plural = 'Perguntas'


class OpcaoPergunta(models.Model):
    pergunta = models.ForeignKey(
        Pergunta, on_delete=models.CASCADE, related_name='opcoes'
    )
    texto = models.CharField(max_length=300)

    def __str__(self):
        return self.texto

    class Meta:
        verbose_name = 'Opção'
        verbose_name_plural = 'Opções'


class RespostaFormulario(models.Model):
    formulario = models.ForeignKey(
        Formulario, on_delete=models.CASCADE, related_name='respostas'
    )
    submetido_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Resposta #{self.pk} — {self.formulario.titulo}'

    class Meta:
        verbose_name = 'Resposta'
        verbose_name_plural = 'Respostas'
        ordering = ['-submetido_em']


class ItemResposta(models.Model):
    resposta = models.ForeignKey(
        RespostaFormulario, on_delete=models.CASCADE, related_name='itens'
    )
    pergunta_id = models.CharField(max_length=100)
    valor = models.TextField()

    def __str__(self):
        return f'{self.pergunta_id}: {self.valor}'

    class Meta:
        verbose_name = 'Item de Resposta'
        verbose_name_plural = 'Itens de Resposta'


class SavedAnalysis(models.Model):
    name = models.CharField(max_length=300)
    notes = models.TextField(blank=True, default='')
    source_type = models.CharField(max_length=20, default='csv')
    source_name = models.CharField(max_length=300, blank=True, default='')
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def to_summary(self):
        columns = self.data.get('columns', [])
        return {
            'id': self.pk,
            'name': self.name,
            'notes': self.notes,
            'source_type': self.source_type,
            'source_name': self.source_name,
            'column_count': len(columns),
            'total_responses': self.data.get('total_responses', 0),
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M'),
        }

    class Meta:
        verbose_name = 'Análise Salva'
        verbose_name_plural = 'Análises Salvas'
        ordering = ['-created_at']
