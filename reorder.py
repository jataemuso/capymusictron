import json

def reorder_json(original_json, new_order_titles):
    """
    Reordena um JSON baseado na ordem e estrutura fornecida em new_order_titles,
    adicionando itens apenas se `downloaded` for True.

    Args:
        original_json (list): Lista de dicionários representando o JSON original.
        new_order_titles (list): Lista de dicionários com a nova ordem e possíveis campos adicionais.

    Returns:
        list: JSON reorganizado.
    """
    # Validando entrada
    if isinstance(original_json, str):
        if not original_json.strip():
            raise ValueError("Erro: original_json é uma string vazia ou inválida.")
        try:
            print("Tentando carregar original_json como string JSON...")
            original_json = json.loads(original_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Erro ao decodificar original_json: {e}")

    if isinstance(new_order_titles, str):
        if not new_order_titles.strip():
            raise ValueError("Erro: new_order_titles é uma string vazia ou inválida.")
        try:
            print("Tentando carregar new_order_titles como string JSON...")
            new_order_titles = json.loads(new_order_titles)
        except json.JSONDecodeError as e:
            raise ValueError(f"Erro ao decodificar new_order_titles: {e}")

    if not isinstance(original_json, list) or not isinstance(new_order_titles, list):
        raise TypeError("Ambos original_json e new_order_titles devem ser listas de dicionários.")

    print("Validando estrutura de original_json e new_order_titles...")

    # Criando um dicionário de referência para os itens existentes
    try:
        original_dict = {item['title']: item for item in original_json}
    except KeyError as e:
        raise KeyError(f"Erro: Chave esperada ausente no original_json: {e}")

    # Rearranjando a ordem com base nos títulos da nova lista
    reordered_json = []
    for item in new_order_titles:
        real_title = item.get('real_title')
        if not real_title:
            print("Erro: 'real_title' não encontrado em new_order_titles.")
            continue

        if not item.get('downloaded', False):  # Verifica se o item foi baixado
            print(f"Ignorando item '{real_title}' porque 'downloaded' é False ou ausente.")
            continue

        if real_title in original_dict:
            print(f"Atualizando item existente: {real_title}")
            reordered_item = original_dict[real_title]
            reordered_item.update(item)  # Atualiza com os novos campos
            reordered_json.append(reordered_item)
        else:
            print(f"Adicionando novo item: {real_title}")
            # Caso o título não exista no JSON original, adiciona os dados do new_order_titles
            reordered_json.append(item)

    # Sobrescrevendo o JSON original
    original_json.clear()
    original_json.extend(reordered_json)

    print("JSON reorganizado com sucesso.")
    return original_json

# Função para carregar o arquivo music_queue.json e chamar reorder_json
def process_music_queue(new_order_titles):
    try:
        with open('music_queue.json', 'r', encoding='utf-8') as file:
            music_queue = json.load(file)
    except FileNotFoundError:
        print("Erro: Arquivo 'music_queue.json' não encontrado.")
        return
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar o arquivo JSON: {e}")
        return
    
    # Reorganiza o JSON com base nos dados de 'new_order_titles'
    print("Iniciando reorganização do JSON...")
    reorder_json(music_queue, new_order_titles)

    # Salvando o JSON reorganizado de volta no arquivo original
    with open('music_queue.json', 'w', encoding='utf-8') as file:
        json.dump(music_queue, file, ensure_ascii=False, indent=4)

    print("JSON reorganizado salvo em 'music_queue.json'.")

# Chamada da função para processar o music_queue.json
# process_music_queue(new_order_titles)
