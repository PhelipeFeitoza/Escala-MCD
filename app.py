import pandas as pd
import streamlit as st

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gestão Field Service McDonalds", layout="wide")

st.title("📊 Dashboard Operacional - Field Service")

# 1. SIMULAÇÃO DE DADOS (O que virá da sua planilha)
# Criando uma base de exemplo com as suas regras
data = {
    'Tecnico': ['Bruno Silva', 'Edwan Vicente', 'Marcio Hoff', 'Alexei Popov', 'Luciano Cardoso'],
    'Regiao': ['SP-Norte', 'NOR-PERNAMBUCO', 'SUL-PORTO ALEGRE', 'SUL-CURITIBA', 'SP-ABC'],
    'Status': ['TB', 'LM', 'TB', 'FG', 'TB'], # TB=Trabalho, LM=Médico, FG=Folga
    'Horario': ['10h-19h', '10h-19h', '13h-22h', '13h-22h', '09h-18h']
}

df = pd.DataFrame(data)

# 2. APLICAÇÃO DAS REGRAS DE NEGÓCIO
def calcular_metas(row):
    # Se status não for TB, não tem capacidade de atendimento
    if row['Status'] != 'TB':
        return 0
    # Regra SP = 4, Outros = 3
    if 'SP' in row['Regiao']:
        return 4
    else:
        return 3

df['Capacity'] = df.apply(calcular_metas, axis=1)

# Identificando Absenteísmo (VAGA, FT, FR, LM)
absenteismo_status = ['FT', 'LM', 'FR', 'VAGA']
df['Is_Absenteismo'] = df['Status'].apply(lambda x: 1 if x in absenteismo_status else 0)

# 3. INTERFACE DO USUÁRIO (SIDEBAR)
st.sidebar.header("Filtros")
regiao_selecionada = st.sidebar.multiselect("Selecione a Região", df['Regiao'].unique(), default=df['Regiao'].unique())

df_filtrado = df[df['Regiao'].isin(regiao_selecionada)]

# 4. DASHBOARD DE INDICADORES (KPIs)
col1, col2, col3 = st.columns(3)

with col1:
    hc_ativo = df_filtrado[df_filtrado['Status'] == 'TB'].shape[0]
    st.metric("Headcount Ativo (Campo)", hc_ativo)

with col2:
    total_capacity = df_filtrado['Capacity'].sum()
    st.metric("Capacidade de Chamados (Dia)", total_capacity)

with col3:
    total_abs = df_filtrado['Is_Absenteismo'].sum()
    st.metric("Absenteísmo", total_abs, delta_color="inverse")

# 5. VISUALIZAÇÃO DA ESCALA
st.subheader("Visualização da Escala")
st.dataframe(df_filtrado[['Tecnico', 'Regiao', 'Horario', 'Status', 'Capacity']], use_container_width=True)

# 6. REGRA DE CORES (Simulando o que você tem no Excel)
def color_status(val):
    if val == 'TB': color = '#C8E6C9' # Verde claro
    elif val == 'LM': color = '#FFCCBC' # Vermelho claro
    elif val == 'FG': color = '#BBDEFB' # Azul claro
    else: color = 'white'
    return f'background-color: {color}'

st.info("💡 Este é um protótipo inicial. Na próxima etapa, conectaremos sua planilha real.")