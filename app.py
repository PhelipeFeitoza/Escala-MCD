import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# Configuração inicial
st.set_page_config(page_title="Sistema de Escala FS", layout="wide")

# --- SIMULAÇÃO DE DADOS PARA O ANO INTEIRO ---
@st.cache_data
def gerar_dados_ano(ano):
    datas = pd.date_range(start=f'{ano}-01-01', end=f'{ano}-12-31')
    tecnicos = ['Bruno Silva', 'Edwan Vicente', 'Marcio Hoff', 'Alexei Popov']
    regioes = ['SP-Norte', 'NOR-PE', 'SUL-POA', 'SUL-CTB']
    
    lista_final = []
    for i, nome in enumerate(tecnicos):
        for data in datas:
            # Simulando uma escala (Aqui entraria o seu Excel real depois)
            status = 'TB' if data.weekday() < 5 else 'FG'
            lista_final.append({
                'Data': data,
                'Tecnico': nome,
                'Regiao': regioes[i],
                'Status': status
            })
    return pd.DataFrame(lista_final)

df_ano = gerar_dados_ano(2026)

# --- INTERFACE ---
st.title("📅 Visualização de Escalas e Ponto")

# Seleção de Visão
visao = st.sidebar.radio(
    "Escolha a Visão:",
    ["📅 Semanal", "📆 Mensal", "📋 Espelho de Ponto (28-27)", "🗓️ Anual (Individual)"]
)

# Filtro de Técnico (Essencial para não travar a tela com 80 pessoas)
tecnico_foco = st.sidebar.selectbox("Selecione o Técnico:", df_ano['Tecnico'].unique())

# --- LÓGICA DAS VISÕES ---

if visao == "📅 Semanal":
    st.header(f"Escala Semanal - {tecnico_foco}")
    hoje = datetime.now()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    
    mask = (df_ano['Data'].dt.date >= inicio_semana.date()) & (df_ano['Data'].dt.date <= fim_semana.date())
    df_semana = df_ano[mask]
    
    # Transpondo para ficar fácil de ler (Dias nas colunas)
    st.table(df_semana[df_semana['Tecnico'] == tecnico_foco].pivot(index='Tecnico', columns='Data', values='Status'))

elif visao == "📆 Mensal":
    mes = st.sidebar.selectbox("Mês:", range(1, 13), index=datetime.now().month - 1)
    st.header(f"Visão Mensal (Calendário Civil) - Mês {mes}")
    
    df_mes = df_ano[(df_ano['Data'].dt.month == mes) & (df_ano['Tecnico'] == tecnico_foco)]
    st.dataframe(df_mes.pivot(index='Tecnico', columns='Data', values='Status'), use_container_width=True)

elif visao == "📋 Espelho de Ponto (28-27)":
    st.header(f"Fechamento de Ponto - {tecnico_foco}")
    mes_referencia = st.sidebar.selectbox("Referência do Fechamento:", 
                                         ["Abril (28/03 a 27/04)", "Maio (28/04 a 27/05)"])
    
    # Exemplo de lógica para o período 28/03 a 27/04
    if "Abril" in mes_referencia:
        inicio = datetime(2026, 3, 28)
        fim = datetime(2026, 4, 27)
    
    mask = (df_ano['Data'] >= inicio) & (df_ano['Data'] <= fim)
    df_ponto = df_ano[mask & (df_ano['Tecnico'] == tecnico_foco)]
    
    # Cálculos para o Gestor
    col1, col2, col3 = st.columns(3)
    col1.metric("Dias Trabalhados", len(df_ponto[df_ponto['Status'] == 'TB']))
    col2.metric("Folgas", len(df_ponto[df_ponto['Status'] == 'FG']))
    col3.metric("Faltas/Afastamentos", len(df_ponto[df_ponto['Status'].isin(['FT', 'LM'])]))

    st.table(df_ponto[['Data', 'Status']].set_index('Data'))

elif visao == "🗓️ Anual (Individual)":
    st.header(f"Escala Completa 2026 - {tecnico_foco}")
    df_anual = df_ano[df_ano['Tecnico'] == tecnico_foco]
    # Aqui usamos uma visualização de grade para o ano todo
    df_pivot_anual = df_anual.pivot(index='Tecnico', columns='Data', values='Status')
    st.dataframe(df_pivot_anual, use_container_width=True)
