import pandas as pd
import random
import numpy as np


def order_list(lista):
    if lista is None:
        return lista

    # Cria DataFrame a partir da lista
    df = pd.DataFrame(lista)
    
    # DataFrame vazio para armazenar a fila ordenada
    df_ordered = []
    df_playnext = df[df['playnext'] == True]

    for i in range(len(df_playnext)):
        df_ordered.append(df_playnext.iloc[i].to_dict())

    # Determina o número máximo de músicas por usuário
    max_music_user = df.groupby('added_by').size().max()

    # Organiza as músicas por usuário, alternando entre os usuários
    for i in range(max_music_user):
        for user, group in df.groupby('added_by', sort=False):
            if i < len(group):
                # Adiciona a música do usuário no índice i à lista ordenada
                df_ordered.append(group.iloc[i].to_dict())

    # Retorna a lista ordenada de dicionários
    return df_ordered


if __name__ == "__main__":
    # Exemplo de FILA_TUDO com 20 músicas de 3 usuários diferentes
    FILA_TUDO = [
        {'title': f'music {i}', 'added_by': f'user {random.randint(1, 4)}', 'downloaded': True, 'playnext': False} for i in range(1, 21)
    ]

    FILA_TUDO[0]['playnext'] = True
    #FILA_TUDO[1]['playnext'] = True
    # Exibe a lista original
    print("Original:")
    for item in FILA_TUDO:
        print(item)

    # Ordena a lista
    FILA_TUDO = order_list(FILA_TUDO)
    df = pd.DataFrame(FILA_TUDO)
    print(df)

    # Exibe a lista ordenada
    print("\nOrdenada:")
    for item in FILA_TUDO:
        print(item)


def order_list(df):
    df_ordered = pd.DataFrame(columns=['title', 'added by', 'downloaded'])

    # Adiciona musicas do playnext primeiro
    df_ordered = pd.concat([df_ordered, df[df['play_next'] == True]])

    # Adiciona musicas restantes
    df = df[df['play_next'] == False]
    max_music_user = df.groupby('added by').size().max()
    for i in range(max_music_user):
        for user in df.groupby('added by', sort=False):
            if i < len(user[1]):
                df_ordered = pd.concat(
                    [df_ordered, user[1].iloc[i].to_frame().T], ignore_index=True
                )
    return df_ordered