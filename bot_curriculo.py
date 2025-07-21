import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import io
import re

# --- Configuração do Logger ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Constantes para Estados da Conversa ---
(
    ESCOLHA, NOME, IDADE, ESTADO_CIVIL, TELEFONE, EMAIL,
    FORMA_2GRAU, ANO_2GRAU,

    # Estados genéricos para Formação Acadêmica
    ASK_QTD_GRAD, ASK_FACULDADE, ASK_CURSO, ASK_SITUACAO, ASK_ANO_GRAD,
    ASK_QTD_POS, ASK_POS_FACULDADE, ASK_POS_CURSO, ASK_POS_SITUACAO, ASK_POS_ANO,
    ADD_ACADEMIC_ITEM,

    # Estados genéricos para Experiência Profissional
    TIPO_CONTRATO, 
    EMPRESA, CARGO, ADM, DEM, ATIVIDADES, RESULTADOS, ADD_EMP, 
    MEI_TRABALHOS, 

    # Estados genéricos para Idiomas
    IDIOMAS_SIM, ASK_IDIOMA_INST, ASK_IDIOMA_NOME, ASK_IDIOMA_NIVEL, ASK_IDIOMA_INI, ASK_IDIOMA_FIM, 
    ADD_IDIOMA,

    CURSOS, CANCEL
) = range(37) 

# --- Validações ---
def validar_texto(texto, min_palavras=2):
    return len(texto.strip().split()) >= min_palavras

def validar_email(texto):
    return re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", texto) is not None

def validar_telefone(texto):
    return texto.isdigit() and 8 <= len(texto) <= 15

def validar_ano_ou_cursando(texto):
    if texto.upper() == 'CURSANDO':
        return True
    if not texto.isdigit() or len(texto) != 4:
        return False
    ano = int(texto)
    return 1900 <= ano <= 2100

def validar_ano(texto):
    if not texto.isdigit() or len(texto) != 4:
        return False
    ano = int(texto)
    return 1900 <= ano <= 2100

def validar_nivel_idioma(nivel):
    return nivel.upper() in ['B', 'I', 'A']

def validar_mes_ano(texto):
    return re.match(r"^(0[1-9]|1[0-2])\/\d{4}$", texto) is not None or texto.upper() == 'ATUAL'

# --- PDF Personalizado ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(70, 130, 180) # SteelBlue
        self.rect(0, 0, self.w, 20, 'F')
        self.set_font('helvetica', 'B', 16)
        self.set_text_color(255, 255, 255) # White
        self.cell(0, 10, 'Currículo Profissional', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128) # Gray
        self.cell(0, 10, f'Página {self.page_no()}', new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')

def gerar_pdf(data):
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_text_color(0) # Black
    
    left_margin = 20 
    pdf.set_left_margin(left_margin)
    pdf.set_x(left_margin)

    def secao(titulo):
        pdf.ln(4)
        pdf.set_font('helvetica', 'B', 14)
        pdf.set_text_color(70, 130, 180) # SteelBlue
        pdf.cell(0, 12, titulo, new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Altura do título da seção (mantido em 12mm)
        pdf.set_text_color(0) # Black
        pdf.set_font('helvetica', '', 12)
        pdf.set_x(left_margin)

    secao("Dados Pessoais")
    # Itens de dados pessoais com altura reduzida para 6mm
    pdf.cell(0, 6, f"Nome: {data.get('nome', 'Não informado')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT) 
    pdf.set_x(left_margin)
    pdf.cell(0, 6, f"Idade: {data.get('idade', 'Não informada')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT) 
    pdf.set_x(left_margin)
    pdf.cell(0, 6, f"Estado Civil: {data.get('estado_civil', 'Não informado')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT) 
    pdf.set_x(left_margin)
    pdf.cell(0, 6, f"Telefone: {data.get('telefone', 'Não informado')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT) 
    pdf.set_x(left_margin)
    pdf.cell(0, 6, f"E-mail: {data.get('email', 'Não informado')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT) 
    pdf.set_x(left_margin)

    secao("Formação Acadêmica")
    if data.get('forma_2grau') == 'S':
        ano_2g = data.get('ano_2grau', 'Não informado')
        pdf.cell(0, 6, f"Ensino Médio: Concluído em {ano_2g}", new_x=XPos.LMARGIN, new_y=YPos.NEXT) 
    else:
        pdf.cell(0, 6, f"Ensino Médio: Incompleto", new_x=XPos.LMARGIN, new_y=YPos.NEXT) 
    pdf.set_x(left_margin)

    graduacoes = data.get('graduacoes', [])
    if graduacoes:
        for i, grad in enumerate(graduacoes):
            pdf.ln(1) # Pequeno espaçamento entre as graduações
            pdf.set_x(left_margin)
            pdf.set_font('helvetica', 'B', 11) 
            pdf.cell(0, 7, f"Graduação {i+1}:", new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Título de graduação maior
            pdf.set_font('helvetica', '', 11)
            
            pdf.set_x(left_margin + 5) 
            pdf.cell(0, 5, f"Universidade: {grad.get('faculdade', '')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Reduzido para 5mm
            pdf.set_x(left_margin + 5)
            pdf.cell(0, 5, f"Curso: {grad.get('curso', '')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Reduzido para 5mm
            pdf.set_x(left_margin + 5)
            sit = grad.get('situacao', '')
            if sit == 'C':
                pdf.cell(0, 5, f"Situação: Concluído em {grad.get('ano', '')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Reduzido para 5mm
            else:
                pdf.cell(0, 5, f"Situação: Cursando", new_x=XPos.LMARGIN, new_y=YPos.NEXT) # Reduzido para 5mm
            pdf.set_x(left_margin) 
    else:
        pdf.cell(0, 6, "", new_x=XPos.LMARGIN, new_y=YPos.NEXT) # "Caso não tenha graduação"
        pdf.set_x(left_margin)

    pos_graduacoes = data.get('pos_graduacoes', [])
    if pos_graduacoes:
        for i, pos in enumerate(pos_graduacoes):
            pdf.ln(1) # Pequeno espaçamento entre as pós-graduações
            pdf.set_x(left_margin)
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 7, f"Pós-Graduação {i+1}:", 0, 1) # Título de pós-graduação maior
            pdf.set_font('Arial', '', 11)

            pdf.set_x(left_margin + 5) 
            pdf.cell(0, 5, f"Universidade: {pos.get('faculdade', '')}", 0, 1) # Reduzido para 5mm
            pdf.set_x(left_margin + 5)
            pdf.cell(0, 5, f"Curso: {pos.get('curso', '')}", 0, 1) # Reduzido para 5mm
            pdf.set_x(left_margin + 5)
            sit = pos.get('situacao', '')
            if sit == 'C':
                pdf.cell(0, 5, f"Situação: Concluído em {pos.get('ano', '')}", 0, 1) # Reduzido para 5mm
            else:
                pdf.cell(0, 5, f"Situação: Cursando", 0, 1) # Reduzido para 5mm
            pdf.set_x(left_margin) 
    else:
        pdf.cell(0, 6, "", 0, 1) # Nenhuma pós-graduação informada
        pdf.set_x(left_margin)


    secao("Experiência Profissional")
    
    if data.get('tipo_contrato') == '2':
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 7, "Tipo de Contrato: Microempreendedor Individual (MEI)", 0, 1) 
        pdf.set_x(left_margin)
        pdf.set_font('Arial', '', 12)
        tipos_trabalho = data.get('mei_trabalhos', '')
        if tipos_trabalho:
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 6, "Principais Trabalhos/Serviços:", 0, 1) 
            pdf.set_x(left_margin)
            pdf.set_font('Arial', '', 10)
            for item in tipos_trabalho.split(','):
                if item.strip():
                    pdf.set_x(left_margin + 5) 
                    pdf.multi_cell(0, 5, f"- {item.strip()}", 0, 'L') # Reduzido para 5mm
            pdf.set_x(left_margin) 
        else:
            pdf.cell(0, 6, "", 0, 1) # "Nenhum tipo de trabalho MEI informado"
            pdf.set_x(left_margin)
    
    elif data.get('tipo_contrato') == '1': 
        experiencias = data.get('experiencias', [])
        if experiencias:
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 7, "Tipo de Contrato: CLT", 0, 1) 
            pdf.set_x(left_margin)
            for i, exp in enumerate(experiencias):
                pdf.ln(1) # Pequeno espaçamento entre as experiências
                pdf.set_x(left_margin)
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 7, f"Empresa {i+1}: {exp.get('empresa', '')}", 0, 1) 
                pdf.set_x(left_margin)
                pdf.set_font('Arial', '', 12)
                pdf.cell(0, 5, f"Período: {exp.get('adm', '')} a {exp.get('dem', '')}", 0, 1) # Reduzido para 5mm
                pdf.set_x(left_margin)
                
                atividades = exp.get('atividades', '')
                if atividades:
                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(0, 6, "Principais Atividades:", 0, 1) 
                    pdf.set_x(left_margin)
                    pdf.set_font('Arial', '', 10)
                    for item in atividades.split('\n'):
                        if item.strip():
                            pdf.set_x(left_margin + 5) 
                            pdf.multi_cell(0, 5, f"- {item.strip()}", 0, 'L') # Reduzido para 5mm
                    pdf.set_x(left_margin) 
                
                resultados = exp.get('resultados', '')
                if resultados:
                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(0, 6, "Principais Resultados:", 0, 1) 
                    pdf.set_x(left_margin)
                    pdf.set_font('Arial', '', 10)
                    for item in resultados.split('\n'):
                        if item.strip():
                            pdf.set_x(left_margin + 5) 
                            pdf.multi_cell(0, 5, f"- {item.strip()}", 0, 'L') # Reduzido para 5mm
                    pdf.set_x(left_margin) 
                pdf.ln(1) # Espaçamento entre blocos de experiência
        else:
            pdf.cell(0, 6, "", 0, 1) # "Nenhuma experiência profissional CLT informada"
            pdf.set_x(left_margin)
    else: 
        pdf.cell(0, 6, "", 0, 1) # "Nenhuma experiência profissional informada" 
        pdf.set_x(left_margin)


    secao("Idiomas")
    idiomas = data.get('idiomas', [])
    if idiomas:
        nivel_map = {'B': 'Básico', 'I': 'Intermediário', 'A': 'Avançado'}
        for i, lang in enumerate(idiomas):
            pdf.ln(1) # Pequeno espaçamento entre os idiomas
            pdf.set_x(left_margin)
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 7, f"Idioma {i+1}:", 0, 1) # Título de idioma ligeiramente maior
            pdf.set_font('Arial', '', 11)

            pdf.set_x(left_margin + 5) 
            pdf.cell(0, 5, f"Instituição: {lang.get('instituicao', '')}", 0, 1) # Reduzido para 5mm
            pdf.set_x(left_margin + 5)
            pdf.cell(0, 5, f"Idioma: {lang.get('nome_idioma', '')}", 0, 1) # CORRIGIDO AQUI!
            pdf.set_x(left_margin + 5)
            nivel = lang.get('nivel', '').upper()
            pdf.cell(0, 5, f"Nível: {nivel_map.get(nivel, nivel)}", 0, 1) # Reduzido para 5mm
            pdf.set_x(left_margin + 5)
            
            fim_idioma = lang.get('fim', '')
            if fim_idioma.upper() == 'CURSANDO':
                pdf.cell(0, 5, f"Início: {lang.get('ini', '')}    |    Situação: Cursando", 0, 1) # Reduzido para 5mm
            else:
                pdf.cell(0, 5, f"Início: {lang.get('ini', '')}    |    Conclusão: {fim_idioma}", 0, 1) # Reduzido para 5mm
            pdf.set_x(left_margin) 
    else:
        pdf.cell(0, 6, "", 0, 1) # "Nenhum idioma informado"
        pdf.set_x(left_margin)

    secao("Cursos Adicionais")
    cursos = data.get('cursos', '')
    if cursos:
        for item in cursos.split(','):
            if item.strip(): 
                pdf.set_x(left_margin + 5) 
                pdf.cell(0, 6, f"- {item.strip()}", 0, 1) # Reduzido para 6mm
        pdf.set_x(left_margin) 
    else:
        pdf.cell(0, 6, "", 0, 1) # "Nenhum curso adicional informado" 
        pdf.set_x(left_margin)

    return pdf

# --- Funções Auxiliares Genéricas para Perguntas (Refatoradas) ---

async def ask_text_standard(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt: str, field_key: str, next_state, validation_func=None, error_message: str = "⚠️ Entrada inválida! Tente novamente."):
    text = update.message.text.strip()

    if validation_func and not validation_func(text):
        await update.message.reply_text(error_message)
        return context.user_data.get('current_state')

    if field_key not in ['faculdade', 'curso', 'situacao', 'ano', 'empresa', 'cargo', 'adm', 'dem', 'atividades', 'resultados', 'instituicao', 'nome_idioma', 'nivel', 'ini', 'fim', 'mei_trabalhos']:
        context.user_data[field_key] = text.title() if field_key not in ['email'] else text.lower()
    else: # Lida com os campos dentro de listas (acadêmico, experiência, idioma)
        current_level = context.user_data.get('current_academic_level')
        current_emp_index = context.user_data.get('current_emp_index')
        current_idioma_index = context.user_data.get('current_idioma_index')

        if field_key in ['faculdade', 'curso', 'situacao', 'ano']:
            idx = context.user_data['current_academic_index']
            if idx >= len(context.user_data.get('graduacoes', [])):
                context.user_data.setdefault('graduacoes', []).append({})
            if current_level == 'graduacao':
                context.user_data['graduacoes'][idx][field_key] = text.title()
            elif current_level == 'pos_graduacao':
                context.user_data['pos_graduacoes'][idx][field_key] = text.title()
        elif field_key in ['empresa', 'cargo', 'adm', 'dem', 'atividades', 'resultados']:
            idx = current_emp_index
            if idx >= len(context.user_data.get('experiencias', [])):
                context.user_data.setdefault('experiencias', []).append({})
            
            if field_key in ['atividades', 'resultados'] and text.upper() != 'N':
                context.user_data['experiencias'][idx][field_key] = text.replace(';', '\n')
            elif field_key in ['atividades', 'resultados'] and text.upper() == 'N':
                context.user_data['experiencias'][idx][field_key] = ''
            else:
                context.user_data['experiencias'][idx][field_key] = text.title()
        elif field_key in ['instituicao', 'nome_idioma', 'nivel', 'ini', 'fim']:
            idx = current_idioma_index
            if idx >= len(context.user_data.get('idiomas', [])):
                context.user_data.setdefault('idiomas', []).append({})
            context.user_data['idiomas'][idx][field_key] = text.title() if field_key not in ['nivel', 'ini', 'fim'] else text.upper()


    await update.message.reply_text(prompt, parse_mode='Markdown')
    context.user_data['current_state'] = next_state
    return next_state

# --- FUNÇÕES DO BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "👋 **Olá!** Que bom ter você aqui! Vamos criar seu **Currículo** de forma **simples e gratuita** em poucos minutos.\n\n"
        "Para **começar**, digite *S*. Se preferir sair, digite *N*.",
        parse_mode='Markdown'
    )
    context.user_data['current_state'] = ESCOLHA
    return ESCOLHA

async def escolha(update, context):
    resposta = update.message.text.strip().upper()
    if resposta != 'S':
        await update.message.reply_text("✅ Processo encerrado. Use /start para começar novamente.")
        return ConversationHandler.END
    await update.message.reply_text("📌 Agora, me diga seu **nome completo**, por favor:", parse_mode='Markdown')
    context.user_data['current_state'] = NOME
    return NOME

async def nome(update, context):
    return await ask_text_standard(update, context, "🎂 Qual a sua **idade**? (Apenas números, entre 14 e 99 anos)", 'nome', IDADE, validar_texto, "⚠️ **Nome inválido!** Por favor, digite seu nome completo (mínimo 2 palavras).")

async def idade(update, context):
    idade_text = update.message.text.strip()
    if not idade_text.isdigit() or not (14 <= int(idade_text) <= 99):
        await update.message.reply_text("⚠️ **Idade inválida!** Digite apenas números entre 14 e 99 anos.")
        return IDADE
    context.user_data['idade'] = idade_text
    await update.message.reply_text("💍 Para seguirmos, qual o seu **estado civil**? (Ex: Solteiro(a), Casado(a))", parse_mode='Markdown')
    context.user_data['current_state'] = ESTADO_CIVIL
    return ESTADO_CIVIL

async def estado_civil(update, context):
    context.user_data['estado_civil'] = update.message.text.strip().title()
    await update.message.reply_text("📞 Certo! Agora, me informe seu **telefone** (apenas números, com DDD):", parse_mode='Markdown')
    context.user_data['current_state'] = TELEFONE
    return TELEFONE

async def telefone(update, context):
    tel = update.message.text.strip()
    if not validar_telefone(tel):
        await update.message.reply_text("⚠️ **Telefone inválido!** Use apenas números (8 a 15 dígitos) com DDD.")
        return TELEFONE
    context.user_data['telefone'] = tel
    await update.message.reply_text("📧 Por favor, digite seu **melhor e-mail** para contato:", parse_mode='Markdown')
    context.user_data['current_state'] = EMAIL
    return EMAIL

async def email(update, context):
    email_text = update.message.text.strip()
    if not validar_email(email_text):
        await update.message.reply_text("⚠️ **E-mail inválido!** Por favor, verifique e tente novamente. Ex: seu.email@dominio.com")
        return EMAIL
    context.user_data['email'] = email_text.lower()
    await update.message.reply_text("✅ Vamos para a **Formação Acadêmica**.\nVocê **concluiu** o **Ensino Médio**? Digite *S* para Sim ou *N* para Não.", parse_mode='Markdown')
    context.user_data['current_state'] = FORMA_2GRAU
    return FORMA_2GRAU

async def forma_2grau(update, context):
    resposta = update.message.text.strip().upper()
    if resposta not in ['S', 'N']:
        await update.message.reply_text("⚠️ **Opção inválida!** Por favor, digite *S* para Sim ou *N* para Não:")
        return FORMA_2GRAU
    context.user_data['forma_2grau'] = resposta
    if resposta == 'S':
        await update.message.reply_text("Ótimo! Em que **ano** você **concluiu** o Ensino Médio? (Ex: 2020)", parse_mode='Markdown')
        context.user_data['current_state'] = ANO_2GRAU
        return ANO_2GRAU
    else: 
        context.user_data['ano_2grau'] = ''
        context.user_data['graduacoes'] = [] 
        context.user_data['pos_graduacoes'] = []
        await update.message.reply_text(
            "💼 Agora vamos para a **Experiência Profissional**.\nVocê se identifica como **trabalhador CLT** ou **Microempreendedor Individual (MEI)**?\n\n*1* para **CLT**\n*2* para **MEI**",
            parse_mode='Markdown'
        )
        context.user_data['current_state'] = TIPO_CONTRATO
        context.user_data['current_emp_index'] = 0
        context.user_data['experiencias'] = []
        context.user_data['mei_trabalhos'] = '' 
        return TIPO_CONTRATO

async def ano_2grau(update, context):
    ano = update.message.text.strip()
    if not validar_ano(ano):
        await update.message.reply_text("⚠️ **Ano inválido!** Digite o ano com 4 dígitos. Ex: 2020")
        return ANO_2GRAU
    context.user_data['ano_2grau'] = ano
    context.user_data['graduacoes'] = []
    context.user_data['pos_graduacoes'] = []
    await update.message.reply_text("Interessante! Quantas **Graduações** você possui atualmente? (Digite *0* se não tiver nenhuma)", parse_mode='Markdown')
    context.user_data['current_state'] = ASK_QTD_GRAD
    return ASK_QTD_GRAD

# --- Funções para Formação Acadêmica (Graduação e Pós) ---

async def ask_qtd_grad(update, context):
    qtd = update.message.text.strip()
    if not qtd.isdigit() or int(qtd) < 0:
        await update.message.reply_text("⚠️ **Quantidade inválida!** Digite um número inteiro (Ex: 0, 1, 2).")
        return ASK_QTD_GRAD
    
    context.user_data['qtd_grad'] = int(qtd)
    context.user_data['current_academic_level'] = 'graduacao'
    context.user_data['current_academic_index'] = 0

    if int(qtd) > 0:
        await update.message.reply_text(f"Por favor, digite o nome da **Universidade** ou **Faculdade** da sua Graduação {context.user_data['current_academic_index'] + 1}:", parse_mode='Markdown')
        context.user_data['current_state'] = ASK_FACULDADE
        return ASK_FACULDADE
    else:
        await update.message.reply_text("Ótimo! Quantas **Pós-Graduações** você possui? (Digite *0* se não tiver nenhuma)", parse_mode='Markdown')
        context.user_data['current_state'] = ASK_QTD_POS
        return ASK_QTD_POS

async def ask_faculdade(update, context):
    return await ask_text_standard(update, context, 
                                   f"Qual é o **Curso** da Graduação {context.user_data['current_academic_index'] + 1}? (Ex: Engenharia Civil)", 
                                   'faculdade', ASK_CURSO, 
                                   lambda x: bool(x.strip()), "⚠️ **Nome da faculdade inválido!** Por favor, digite o nome da Universidade ou Faculdade.")

async def ask_curso(update, context):
    return await ask_text_standard(update, context, 
                                   f"Qual a **situação** da sua Graduação {context.user_data['current_academic_index'] + 1}? Digite *C* para Concluído ou *I* para Incompleto (Cursando).", 
                                   'curso', ASK_SITUACAO, 
                                   lambda x: bool(x.strip()), "⚠️ **Nome do curso inválido!** Por favor, digite o curso.")

async def ask_situacao(update, context):
    sit = update.message.text.strip().upper()
    if sit not in ['C', 'I']:
        await update.message.reply_text("⚠️ **Opção inválida!** Digite *C* para Concluído ou *I* para Incompleto (Cursando).", parse_mode='Markdown')
        return ASK_SITUACAO
    
    idx = context.user_data['current_academic_index']
    context.user_data['graduacoes'][idx]['situacao'] = sit

    if sit == 'C':
        await update.message.reply_text(f"Em que **ano** a Graduação {idx+1} foi **concluída**? (Ex: 2025)", parse_mode='Markdown')
        context.user_data['current_state'] = ASK_ANO_GRAD
        return ASK_ANO_GRAD
    else:
        context.user_data['graduacoes'][idx]['ano'] = ''
        await update.message.reply_text("Deseja adicionar **outra Graduação**? Digite *S* para Sim ou *N* para Não.", parse_mode='Markdown')
        context.user_data['current_state'] = ADD_ACADEMIC_ITEM
        return ADD_ACADEMIC_ITEM

async def ask_ano_grad(update, context):
    return await ask_text_standard(update, context, 
                                   "Deseja adicionar **outra Graduação**? Digite *S* para Sim ou *N* para Não.", 
                                   'ano', ADD_ACADEMIC_ITEM, 
                                   validar_ano, "⚠️ **Ano inválido!** Digite o ano com 4 dígitos. Ex: 2025")

async def add_academic_item(update, context):
    resposta = update.message.text.strip().upper()
    if resposta not in ['S', 'N']:
        await update.message.reply_text("⚠️ **Opção inválida!** Digite *S* para Sim ou *N* para Não:", parse_mode='Markdown')
        return ADD_ACADEMIC_ITEM

    current_level = context.user_data['current_academic_level']

    if resposta == 'S':
        context.user_data['current_academic_index'] += 1
        if current_level == 'graduacao':
            await update.message.reply_text(f"Qual o nome da **Universidade** ou **Faculdade** da Graduação {context.user_data['current_academic_index'] + 1}?", parse_mode='Markdown')
            context.user_data['current_state'] = ASK_FACULDADE
            return ASK_FACULDADE
        elif current_level == 'pos_graduacao':
            await update.message.reply_text(f"Qual o nome da **Universidade** ou **Faculdade** da Pós-Graduação {context.user_data['current_academic_index'] + 1}?", parse_mode='Markdown')
            context.user_data['current_state'] = ASK_POS_FACULDADE
            return ASK_POS_FACULDADE
    else: # Resposta 'N'
        if current_level == 'graduacao':
            await update.message.reply_text("Ótimo! Quantas **Pós-Graduações** você possui? (Digite *0* se não tiver nenhuma)", parse_mode='Markdown')
            context.user_data['current_state'] = ASK_QTD_POS
            return ASK_QTD_POS
        elif current_level == 'pos_graduacao':
            await update.message.reply_text(
                "💼 Agora vamos para a **Experiência Profissional**.\nVocê se identifica como **trabalhador CLT** ou **Microempreendedor Individual (MEI)**?\n\n*1* para **CLT**\n*2* para **MEI**",
                parse_mode='Markdown'
            )
            context.user_data['current_state'] = TIPO_CONTRATO
            context.user_data['current_emp_index'] = 0
            context.user_data['experiencias'] = []
            context.user_data['mei_trabalhos'] = '' 
            return TIPO_CONTRATO

# Funções para Pós-Graduação
async def ask_qtd_pos(update, context):
    qtd = update.message.text.strip()
    if not qtd.isdigit() or int(qtd) < 0:
        await update.message.reply_text("⚠️ **Quantidade inválida!** Digite um número inteiro (Ex: 0, 1, 2).")
        return ASK_QTD_POS
    
    context.user_data['qtd_pos'] = int(qtd)
    context.user_data['current_academic_level'] = 'pos_graduacao'
    context.user_data['current_academic_index'] = 0

    if int(qtd) > 0:
        await update.message.reply_text(f"Qual o nome da **Universidade** ou **Faculdade** da Pós-Graduação {context.user_data['current_academic_index'] + 1}?", parse_mode='Markdown')
        context.user_data['current_state'] = ASK_POS_FACULDADE
        return ASK_POS_FACULDADE
    else:
        await update.message.reply_text(
            "💼 Agora vamos para a **Experiência Profissional**.\nVocê se identifica como **trabalhador CLT** ou **Microempreendedor Individual (MEI)**?\n\n*1* para **CLT**\n*2* para **MEI**",
            parse_mode='Markdown'
        )
        context.user_data['current_state'] = TIPO_CONTRATO
        context.user_data['current_emp_index'] = 0
        context.user_data['experiencias'] = []
        context.user_data['mei_trabalhos'] = '' 
        return TIPO_CONTRATO

async def ask_pos_faculdade(update, context):
    return await ask_text_standard(update, context, 
                                   f"Qual é o **Curso** da Pós-Graduação {context.user_data['current_academic_index'] + 1}? (Ex: MBA em Gestão)", 
                                   'faculdade', ASK_POS_CURSO, 
                                   lambda x: bool(x.strip()), "⚠️ **Nome da Faculdade inválido!** Por favor, digite o nome da Universidade ou Faculdade.")


async def ask_pos_curso(update, context):
    return await ask_text_standard(update, context, 
                                   f"Qual a **situação** da Pós-Graduação {context.user_data['current_academic_index'] + 1}? Digite *C* para Concluído ou *I* para Incompleto (Cursando).", 
                                   'curso', ASK_POS_SITUACAO, 
                                   lambda x: bool(x.strip()), "⚠️ **Nome do curso inválido!** Por favor, digite o curso.")

async def ask_pos_situacao(update, context):
    sit = update.message.text.strip().upper()
    if sit not in ['C', 'I']:
        await update.message.reply_text("⚠️ **Opção inválida!** Digite *C* para Concluído ou *I* para Incompleto (Cursando).", parse_mode='Markdown')
        return ASK_POS_SITUACAO
    
    idx = context.user_data['current_academic_index']
    context.user_data['pos_graduacoes'][idx]['situacao'] = sit

    if sit == 'C':
        await update.message.reply_text(f"Em que **ano** a Pós-Graduação {idx+1} foi **concluída**? (Ex: 2025)", parse_mode='Markdown')
        context.user_data['current_state'] = ASK_POS_ANO
        return ASK_POS_ANO
    else:
        context.user_data['pos_graduacoes'][idx]['ano'] = ''
        await update.message.reply_text("Deseja adicionar **outra Pós-Graduação**? Digite *S* para Sim ou *N* para Não.", parse_mode='Markdown')
        context.user_data['current_state'] = ADD_ACADEMIC_ITEM
        return ADD_ACADEMIC_ITEM

async def ask_pos_ano(update, context):
    return await ask_text_standard(update, context, 
                                   "Deseja adicionar **outra Pós-Graduação**? Digite *S* para Sim ou *N* para Não.", 
                                   'ano', ADD_ACADEMIC_ITEM, 
                                   validar_ano, "⚠️ **Ano inválido!** Digite o ano com 4 dígitos. Ex: 2025")

# --- Funções para Experiência Profissional ---

async def tipo_contrato(update, context):
    resposta = update.message.text.strip()
    
    if resposta == '1': 
        context.user_data['tipo_contrato'] = '1'
        context.user_data['experiencias'] = [] 
        await update.message.reply_text("🏢 Perfeito! Qual o **nome da última empresa** que você trabalhou com **carteira assinada**?\n\n*Se não houver, digite N para pular esta seção.*", parse_mode='Markdown')
        context.user_data['current_state'] = EMPRESA
        context.user_data['current_emp_index'] = 0
        return EMPRESA
    elif resposta == '2': 
        context.user_data['tipo_contrato'] = '2'
        await update.message.reply_text(
            "Entendido! Como **MEI**, quais são os principais **tipos de trabalho** ou serviços que você realiza? Liste-os **separados por vírgula**.\n\n*Ex: Desenvolvedor Web, Consultor de Marketing, Designer Gráfico*",
            parse_mode='Markdown'
        )
        context.user_data['current_state'] = MEI_TRABALHOS
        context.user_data['experiencias'] = [] 
        return MEI_TRABALHOS
    else:
        await update.message.reply_text("⚠️ **Opção inválida!** Digite *1* para CLT ou *2* para Microempreendedor Individual.", parse_mode='Markdown')
        return TIPO_CONTRATO

async def mei_trabalhos(update, context):
    text = update.message.text.strip()
    context.user_data['mei_trabalhos'] = text
    await update.message.reply_text("🗣️ Chegamos na seção de **Idiomas**! Você possui algum **curso de idioma**?\n\nDigite *S* para Sim ou *N* para Não.", parse_mode='Markdown')
    context.user_data['current_state'] = IDIOMAS_SIM
    context.user_data['current_idioma_index'] = 0
    context.user_data['idiomas'] = []
    return IDIOMAS_SIM

async def empresa(update, context):
    text = update.message.text.strip()
    if text.upper() == 'N':
        await update.message.reply_text("🗣️ Chegamos na seção de **Idiomas**! Você possui algum **curso de idioma**?\n\nDigite *S* para Sim ou *N* para Não.", parse_mode='Markdown')
        context.user_data['current_state'] = IDIOMAS_SIM
        context.user_data['current_idioma_index'] = 0
        context.user_data['idiomas'] = []
        return IDIOMAS_SIM
    
    return await ask_text_standard(update, context, 
                                   f"Qual o **cargo exercido** na {text.title()}?", 
                                   'empresa', CARGO, 
                                   lambda x: bool(x.strip()), "⚠️ **Nome da empresa inválido!** Por favor, digite o nome da empresa ou 'N' para pular.")

async def cargo(update, context):
    return await ask_text_standard(update, context, 
                                   "Agora, qual a **data de admissão**? (Fotmato obrigatório MM/YYYY. Ex: 01/2020)", 
                                   'cargo', ADM, 
                                   lambda x: bool(x.strip()), "⚠️ **Cargo inválido!** Por favor, digite o cargo exercido.")

async def adm(update, context):
    return await ask_text_standard(update, context, 
                                   "E a **data de demissão ou saída**? (Formato obrigatório MM/YYYY ou 'Atual'. Ex: 12/2022 ou Atual)", 
                                   'adm', DEM, 
                                   validar_mes_ano, "⚠️ **Data inválida!** Fotmato obrigatório MM/YYYY ou 'Atual'.")

async def dem(update, context):
    return await ask_text_standard(update, context, 
                                   "Liste suas **principais atividades e responsabilidades** neste cargo.\nVocê pode usar uma por linha ou separá-las por ponto e vírgula (;).\n\n*Exemplo:*\n*- Gestão de projetos*\n*- Desenvolvimento de software*\n\n*Se preferir não informar, digite N.*", 
                                   'dem', ATIVIDADES, 
                                   validar_mes_ano, "⚠️ **Data inválida!** Formato obrigatório MM/YYYY ou 'Atual'.")

async def atividades(update, context):
    return await ask_text_standard(update, context, 
                                   "Excelente! E quais foram seus **principais resultados ou conquistas** nessa experiência? (Seja específico, com números se possível!)\n\nVocê pode usar uma por linha ou separá-las por ponto e vírgula (;).\n\n*Exemplo:*\n*- Redução de custos em 15%*\n*- Aumento de vendas em 20%*\n\n*Se preferir não informar, digite N.*", 
                                   'atividades', RESULTADOS, 
                                   lambda x: True) 

async def resultados(update, context):
    return await ask_text_standard(update, context, 
                                   "Deseja adicionar **outra Experiência Profissional**? Digite *S* para Sim ou *N* para Não.", 
                                   'resultados', ADD_EMP, 
                                   lambda x: True) 
      
async def add_emp(update, context):
    resposta = update.message.text.strip().upper()
    if resposta not in ['S', 'N']:
        await update.message.reply_text("⚠️ **Opção inválida!** Digite *S* para Sim ou *N* para Não:", parse_mode='Markdown')
        return ADD_EMP
    
    if resposta == 'S':
        context.user_data['current_emp_index'] += 1
        await update.message.reply_text(f"Qual o **nome da próxima empresa** (Experiência {context.user_data['current_emp_index'] + 1})?\n\n*Se não houver, digite N para pular esta seção.*", parse_mode='Markdown')
        context.user_data['current_state'] = EMPRESA
        return EMPRESA
    else:
        await update.message.reply_text("🗣️ Chegamos na seção de **Idiomas**! Você possui algum **curso de idioma**?\n\nDigite *S* para Sim ou *N* para Não.", parse_mode='Markdown')
        context.user_data['current_state'] = IDIOMAS_SIM
        context.user_data['current_idioma_index'] = 0
        context.user_data['idiomas'] = []
        return IDIOMAS_SIM

# --- Funções para Idiomas ---
async def idiomas_sim(update, context):
    resposta = update.message.text.strip().upper()
    if resposta not in ['S', 'N']:
        await update.message.reply_text("⚠️ **Opção inválida!** Responda *S* para Sim ou *N* para Não:", parse_mode='Markdown')
        return IDIOMAS_SIM

    if resposta == 'N':
        await update.message.reply_text("📚 Para finalizar, liste seus **Cursos adicionais** e **Certificações** (se houver), separados por vírgula.\n\n*Ex: Java, JavaScript, Excel Avançado, Liderança e Gestão de Equipes*", parse_mode='Markdown')
        context.user_data['current_state'] = CURSOS
        return CURSOS
    else:
        context.user_data['current_idioma_index'] = 0
        context.user_data['idiomas'] = []
        await update.message.reply_text(f"Qual a **instituição** do idioma {context.user_data['current_idioma_index'] + 1}?", parse_mode='Markdown')
        context.user_data['current_state'] = ASK_IDIOMA_INST
        return ASK_IDIOMA_INST

async def ask_idioma_inst(update, context):
    return await ask_text_standard(update, context, 
                                   f"Qual o **nome do idioma** {context.user_data['current_idioma_index'] + 1}? (Ex: Inglês)", 
                                   'instituicao', ASK_IDIOMA_NOME, 
                                   lambda x: bool(x.strip()), "⚠️ **Instituição inválida!** Por favor, digite o nome da instituição do idioma.")

async def ask_idioma_nome(update, context):
    # AQUI O FIELD_KEY FOI ALTERADO PARA 'nome_idioma' PARA BATER COM O PDF
    return await ask_text_standard(update, context, 
                                   f"Qual o **nível de proficiência** do idioma {context.user_data['current_idioma_index'] + 1}? Digite a letra correspondente:\n\n*B* para **Básico**\n*I* para **Intermediário**\n*A* para **Avançado**", 
                                   'nome_idioma', ASK_IDIOMA_NIVEL, # <- field_key CORRIGIDO AQUI
                                   lambda x: bool(x.strip()), "⚠️ **Nome do idioma inválido!** Por favor, digite o nome do idioma.")

async def ask_idioma_nivel(update, context):
    nivel = update.message.text.strip().upper()
    if not validar_nivel_idioma(nivel):
        await update.message.reply_text("⚠️ **Nível inválido!** Digite *B* (Básico), *I* (Intermediário) ou *A* (Avançado).", parse_mode='Markdown')
        return ASK_IDIOMA_NIVEL
    
    idx = context.user_data['current_idioma_index']
    context.user_data['idiomas'][idx]['nivel'] = nivel
    await update.message.reply_text(f"Em que **ano** você **iniciou** o curso de idioma {idx+1}? (Ex: 2020)", parse_mode='Markdown') 
    context.user_data['current_state'] = ASK_IDIOMA_INI
    return ASK_IDIOMA_INI

async def ask_idioma_ini(update, context):
    return await ask_text_standard(update, context, 
                                   f"Em que **ano** você **concluiu** o idioma {context.user_data['current_idioma_index'] + 1}? Ou digite **Cursando** se ainda estiver estudando.\n\n*Ex: 2018 ou Cursando*", 
                                   'ini', ASK_IDIOMA_FIM, 
                                   validar_ano, "⚠️ **Ano inválido!** Digite o ano com 4 dígitos. Ex: 2020.")

async def ask_idioma_fim(update, context):
    return await ask_text_standard(update, context, 
                                   "Deseja adicionar **outro idioma**? Digite *S* para Sim ou *N* para Não.", 
                                   'fim', ADD_IDIOMA, 
                                   validar_ano_ou_cursando, "⚠️ **Entrada inválida!** Digite o ano com 4 dígitos (Ex: 2018) ou 'Cursando'.")

async def add_idioma(update, context):
    resposta = update.message.text.strip().upper()
    if resposta not in ['S', 'N']:
        await update.message.reply_text("⚠️ **Opção inválida!** Digite *S* para Sim ou *N* para Não:", parse_mode='Markdown')
        return ADD_IDIOMA
    
    if resposta == 'S':
        context.user_data['current_idioma_index'] += 1
        await update.message.reply_text(f"Qual a **instituição** do idioma {context.user_data['current_idioma_index'] + 1}?", parse_mode='Markdown')
        context.user_data['current_state'] = ASK_IDIOMA_INST
        return ASK_IDIOMA_INST
    else:
        await update.message.reply_text("📚 Para finalizar, liste seus **cursos adicionais** e **certificações** (se houver), separados por vírgula.\n\n*Ex: Java, JavaScript, Excel Avançado, Liderança e Gestão de Equipes*", parse_mode='Markdown')
        context.user_data['current_state'] = CURSOS
        return CURSOS

# --- Funções para Cursos Adicionais e Geração Automática do PDF ---

async def cursos(update, context):
    cursos_texto = update.message.text.strip()
    context.user_data['cursos'] = cursos_texto

    await update.message.reply_text("🎉 **Parabéns!** Seu currículo foi **gerado com sucesso** e está sendo enviado para você agora mesmo!\n\nPor favor, **verifique o arquivo PDF** anexo.", parse_mode='Markdown')

    pdf = gerar_pdf(context.user_data)
    pdf_bytes = pdf.output()
    bio = io.BytesIO(pdf_bytes)
    bio.name = "curriculo.pdf"
    bio.seek(0)

    await update.message.reply_document(document=bio, filename="curriculo.pdf")

    await update.message.reply_text(
        "---"
        "✨ **Processo concluído!** Sempre que precisar criar um novo currículo ou ajustar algo, é só digitar */start* novamente.",
        parse_mode='Markdown'
    )

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Processo cancelado. Use /start para recomeçar."
    )
    return ConversationHandler.END

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN não encontrado nas variáveis de ambiente!")
        return
    
    application = ApplicationBuilder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ESCOLHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, escolha)],
            NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, nome)],
            IDADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, idade)],
            ESTADO_CIVIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, estado_civil)],
            TELEFONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, telefone)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email)],
            FORMA_2GRAU: [MessageHandler(filters.TEXT & ~filters.COMMAND, forma_2grau)],
            ANO_2GRAU: [MessageHandler(filters.TEXT & ~filters.COMMAND, ano_2grau)],

            # Formação Acadêmica
            ASK_QTD_GRAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_qtd_grad)],
            ASK_FACULDADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_faculdade)],
            ASK_CURSO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_curso)],
            ASK_SITUACAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_situacao)],
            ASK_ANO_GRAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_ano_grad)],
            ASK_QTD_POS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_qtd_pos)],
            ASK_POS_FACULDADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pos_faculdade)],
            ASK_POS_CURSO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pos_curso)],
            ASK_POS_SITUACAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pos_situacao)],
            ASK_POS_ANO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pos_ano)],
            ADD_ACADEMIC_ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_academic_item)],

            # Experiência Profissional
            TIPO_CONTRATO: [MessageHandler(filters.TEXT & ~filters.COMMAND, tipo_contrato)],
            MEI_TRABALHOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, mei_trabalhos)],
            EMPRESA: [MessageHandler(filters.TEXT & ~filters.COMMAND, empresa)],
            CARGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, cargo)],
            ADM: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm)],
            DEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, dem)],
            ATIVIDADES: [MessageHandler(filters.TEXT & ~filters.COMMAND, atividades)],
            RESULTADOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, resultados)],
            ADD_EMP: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_emp)],

            # Idiomas
            IDIOMAS_SIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, idiomas_sim)],
            ASK_IDIOMA_INST: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_idioma_inst)],
            ASK_IDIOMA_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_idioma_nome)],
            ASK_IDIOMA_NIVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_idioma_nivel)],
            ASK_IDIOMA_INI: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_idioma_ini)],
            ASK_IDIOMA_FIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_idioma_fim)],
            ADD_IDIOMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_idioma)],

            CURSOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, cursos)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    print("🤖 Bot rodando...")
    application.run_polling()

if __name__ == "__main__":
    main()