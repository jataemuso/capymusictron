import pandas as pd
import random
import numpy as np

FILA_TUDO = [
    {'title': f'music {i}', 'added by': f'user {random.randint(1,3)}', 'downloaded': True} for i in range(1, 20)
]

df = pd.DataFrame(FILA_TUDO)
print(df)


for user in df.groupby('added by'):
    print(f'User: {user[0]}')
    df_user = user[1].copy()
    print(df_user.reset_index())
    print('---')


def order_list(lista):
    df = pd.DataFrame(lista)
    df_ordered = pd.DataFrame(columns=['title', 'added by', 'downloaded'])
    max_music_user = df.groupby('added by').size().max()
    for i in range(max_music_user):
        for user in df.groupby('added by'):
            if i < len(user[1]):
                df_ordered = pd.concat(
                    [df_ordered, user[1].iloc[i].to_frame().T], ignore_index=True
                )
    # Converter os valores booleanos para o tipo nativo Python antes de retornar
    fila_ordenada = df_ordered.applymap(
        lambda x: bool(x) if isinstance(x, (bool, np.bool_)) else x
    ).values.tolist()
    return fila_ordenada


FILA_TUDO = order_list(FILA_TUDO)


for item in FILA_TUDO:
    print(item)
