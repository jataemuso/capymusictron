import streamlit as st
import pandas as pd
import plotly.express as px

# Configurações iniciais do Streamlit
st.set_page_config(page_title="Dashboard do Bot", layout="wide")

# Carregar dados
def load_data():
    date = st.sidebar.date_input("Selecione a data", value=pd.Timestamp.now().date())
    file_path = f"logs/{date}_commands.csv"
    try:
        data = pd.read_csv(file_path)
        return data
    except FileNotFoundError:
        st.error(f"Dados de {date} não encontrados.")
        return pd.DataFrame()

df = load_data()

# Verificar se há dados
if not df.empty:
    # Resumo geral
    st.title("Dashboard do Bot")
    st.markdown(f"### Resumo de Atividade - {len(df)} comandos registrados")
    nope = ['user_id', 'server_id', 'channel_id']
    df_display = df[[coluna for coluna in df.columns if coluna not in nope]].reindex(index=df.index[::-1])
    st.write(df_display)

    # Análise de Comandos
    st.markdown("## Comandos mais usados")
    command_counts = df['command'].value_counts().reset_index()
    command_counts.columns = ['Comando', 'Frequência']
    fig1 = px.bar(command_counts, x='Comando', y='Frequência', title="Comandos mais usados")
    st.plotly_chart(fig1, use_container_width=True)

    # Atividade por Servidor
    st.markdown("## Atividade por Servidor")
    if 'server' in df.columns:
        server_activity = df.groupby('server')['command'].count().reset_index()
        server_activity.columns = ['Servidor', 'Comandos']
        fig2 = px.pie(server_activity, values='Comandos', names='Servidor', title="Comandos por Servidor")
        st.plotly_chart(fig2, use_container_width=True)

        tempo_de_reproducao = df.groupby('server')['tempo_de_reproducao_acumulado'].last().reset_index()
        print(tempo_de_reproducao)
        tempo_de_reproducao.columns = ['Servidor', 'Tempo de Reprodução']
        fig5 = px.pie(
            tempo_de_reproducao, 
            values='Tempo de Reprodução', 
            names='Servidor', 
            title='Tempo de Reprodução por Servidor'
            )
        st.plotly_chart(fig5, use_container_width=True)

    # Atividade por Canal
    if 'channel' in df.columns:
        st.markdown("## Atividade por Canal")
        channel_activity = df.groupby('channel')['command'].count().reset_index()
        channel_activity.columns = ['Canal', 'Comandos']
        fig3 = px.bar(channel_activity, x='Canal', y='Comandos', title="Atividade por Canal", color='Canal')
        st.plotly_chart(fig3, use_container_width=True)

    # Análise temporal
    if 'timestamp' in df.columns:
        st.markdown("## Atividade ao longo do tempo")
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hora'] = df['timestamp'].dt.hour
        hourly_activity = df.groupby('hora')['command'].count().reset_index()
        hourly_activity.columns = ['Hora', 'Comandos']
        fig4 = px.line(hourly_activity, x='Hora', y='Comandos', title="Atividade por Hora do Dia")
        st.plotly_chart(fig4, use_container_width=True)

else:
    st.warning("Carregue os dados para visualizar o dashboard.")
