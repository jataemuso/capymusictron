import json

# Caminho para o arquivo JSON
config_file = "server_config.json"

# Configurações padrão
default_config = {
    "id_dj": None,
    "fair_queue": True
}

# Funções para gerenciar configurações
def load_servers(filepath=config_file):
    """Carrega as configurações dos servidores do arquivo JSON."""
    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print("Arquivo não encontrado. Criando um novo.")
        return {}
    except json.JSONDecodeError:
        print("Erro no formato do arquivo JSON. Criando um novo.")
        return {}

def save_servers(servers, filepath=config_file):
    """Salva as configurações dos servidores no arquivo JSON."""
    try:
        with open(filepath, 'w') as file:
            json.dump(servers, file, indent=4)
        print("Configurações salvas com sucesso.")
    except Exception as e:
        print(f"Erro ao salvar configurações: {e}")

def add_server(servers, server_id):
    """Adiciona um novo servidor com as configurações padrão."""
    if str(server_id) in servers:
        print(f"Servidor com ID '{server_id}' já existe.")
        return False
    servers[server_id] = default_config.copy()  # Usa uma cópia das configurações padrão
    print(f"Servidor '{server_id}' adicionado com sucesso.")
    return True

def update_server(servers, server_id, **kwargs):
    """Atualiza as configurações de um servidor existente."""
    if server_id not in servers:
        print(f"Servidor com ID '{server_id}' não encontrado.")
        return False
    servers[server_id].update(kwargs)
    print(f"Servidor '{server_id}' atualizado com sucesso.")
    return True

def remove_server(servers, server_id):
    """Remove um servidor pelo ID."""
    if server_id in servers:
        del servers[server_id]
        print(f"Servidor '{server_id}' removido com sucesso.")
        return True
    print(f"Servidor com ID '{server_id}' não encontrado.")
    return False

# Exemplo de uso
if __name__ == "__main__":
    # Carrega as configurações
    servers = load_servers()

    # Adiciona novos servidores
    add_server(servers, "server_1")
    add_server(servers, "server_2")

    # Atualiza configurações de um servidor
    update_server(servers, "server_1", id_dj="DJ123", fair_queue=False)

    # Tenta adicionar um servidor duplicado
    add_server(servers, "server_1")

    # Remove um servidor
    remove_server(servers, "server_2")

    # Salva as alterações
    save_servers(servers)

    # Confere os dados finais
    print("Configurações finais dos servidores:", servers)
