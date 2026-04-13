import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# Configuração da Página
st.set_page_config(page_title="Gestão de Escala FS", layout="wide")

# --- GERADOR DE DATAS E NOMES (SIMULADO) ---
@st.cache_data
def carregar_dados_base():
    datas = pd.date_range(start='2026-01-01', end='2026-12-31')
    tecnicos = [f"Técnico {i}" for i in range(1, 81)] # Seus 80 técnicos
    
    # Criando DataFrame base
    df_lista = []
    for t in tecnicos:
        for d in datas:
            status = 'TB' if d.weekday() < 5 else 'FG'
            df_lista.append({'Data': d, 'Tecnico': t, 'Status': status})
    return pd.DataFrame(df_lista)

df_base = carregar_dados_base()

# --- FUNÇÕES DE FORMATAÇÃO ---
def formatar_colunas_data(df_pivot):
    """ Transforma a data do cabeçalho em 'seg 13/04' """
    novas_colunas = []
    dias_semana = {0: 'seg', 1: 'ter', 2: 'qua', 3: 'qui', 4: 'sex', 5: 'sáb', 6: 'dom'}
    for col in df_pivot.columns:
        if isinstance(col, datetime) or str(type(col)) == "<class 'pandas._libs.tslibs.timestamps.Timestamp'>":
            dia_sem = dias_semana[col.weekday()]
            data_formatada = col.strftime('%d/%m')
            novas_colunas.append(f"{dia_sem} {data_formatada}")
        else:
            novas_colunas.append(col)
    df_pivot.columns = novas_colunas
    return df_pivot

def colorir_status(val):
    """ Aplica as cores conforme o status (estilo Excel) """
    cores = {
        'TB': 'background-color: #C8E6C9; color: black;', # Verde
        'FG': 'background-color: #BBDEFB; color: black;', # Azul
        'LM': 'background-color: #FFCDD2; color: black;', # Vermelho
        'FT': 'background-color: #EF9A9A; color: black;', # Vermelho Forte
        'TR': 'background-color: #FFF9C4; color: black;', # Amarelo
        'PV': 'background-color: #E1BEE7; color: black;'  # Roxo
    }
    return cores.get(val, '')

# --- INTERFACE ---
st.title("📊 Painel de Controle de Escalas")

menu = ["Semanal (Gestor)", "Mensal (Gestor)", "Espelho de Ponto (28-27)", "Anual"]
escolha = st.sidebar.selectbox("Mudar Visão", menu)

# --- VISÃO SEMANAL (GESTO) ---
if escolha == "Semanal (Gestor)":
    st.subheader("Escala Semanal - Todos os Técnicos")
    data_ref = st.sidebar.date_input("Selecione a semana (qualquer dia):", datetime(2026, 4, 13))
    inicio_sem = data_ref - timedelta(days=data_ref.weekday())
    fim_sem = inicio_sem + timedelta(days=6)
    
    mask = (df_base['Data'].dt.date >= inicio_sem) & (df_base['Data'].dt.date <= fim_sem)
    df_view = df_base[mask].pivot(index='Tecnico', columns='Data', values='Status')
    df_view = formatar_colunas_data(df_view)
    
    st.dataframe(df_view.style.applymap(colorir_status), use_container_width=True)

# --- VISÃO MENSAL (GESTOR) ---
elif escolha == "Mensal (Gestor)":
    mes = st.sidebar.slider("Selecione o Mês", 1, 12, 4)
    st.subheader(f"Visão Mensal - Mês {mes}")
    
    mask = (df_base['Data'].dt.month == mes)
    df_view = df_base[mask].pivot(index='Tecnico', columns='Data', values='Status')
    df_view = formatar_colunas_data(df_view)
    
    st.dataframe(df_view.style.applymap(colorir_status), height=600)

# --- VISÃO ESPELHO DE PONTO (28 a 27) ---
elif escolha == "Espelho de Ponto (28-27)":
    st.subheader("Conferência de Espelho de Ponto")
    tecnico = st.selectbox("Selecione o Técnico para conferência:", df_base['Tecnico'].unique())
    mes_fim = st.sidebar.selectbox("Mês de Fechamento (até o dia 27):", 
                                  ["Abril (28/03 a 27/04)", "Maio (28/04 a 27/05)"])
    
    # Lógica de datas para o Ponto
    if "Abril" in mes_fim:
        ini, fim = datetime(2026, 3, 28), datetime(2026, 4, 27)
    else:
        ini, fim = datetime(2026, 4, 28), datetime(2026, 5, 27)
        
    mask = (df_base['Data'] >= ini) & (df_base['Data'] <= fim) & (df_base['Tecnico'] == tecnico)
    df_ponto = df_base[mask].copy()
    
    # Adicionando dia da semana para o técnico ver
    df_ponto['Dia'] = df_ponto['Data'].dt.strftime('%a %d/%m')
    
    # Exibição
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Total Dias Trabalhados", len(df_ponto[df_ponto['Status'] == 'TB']))
        st.dataframe(df_ponto[['Dia', 'Status']].set_index('Dia').style.applymap(colorir_status))
    with col2:
        st.info("Aqui você pode validar as horas extras ou observações do período.")

# --- VISÃO ANUAL ---
elif escolha == "Anual":
    st.subheader("Visão Anual Completa (Empilhada)")
    # Nota: Mostrar 365 colunas para 80 técnicos é pesado, usamos scroll
    df_view = df_base.pivot(index='Tecnico', columns='Data', values='Status')
    st.dataframe(df_view.style.applymap(colorir_status), height=600)
