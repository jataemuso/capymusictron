# CapyMusictron

A Discord music bot focused on queue management, useful features, and an activity dashboard.

## Overview

CapyMusictron is a Discord music bot developed in Python, utilizing the `discord.py` library, `yt-dlp`, `ytmusicapi`, and other tools to provide a complete and customizable audio experience on servers. It stands out for its fair queue system, flexible permissions management, and an interactive dashboard for analyzing bot usage.

This bot offers a range of functionalities, including:

-   **Music Playback:** Adds and plays music from YouTube links or title searches.
-   **Queue Management:** Displays, organizes, skips, removes, and clears the music queue.
-   **Custom Queues:** A fair queue system that prioritizes "playnext" songs and alternates songs between users, ensuring everyone gets their music played.
-   **Custom Radios:** Creates automatic playlists based on a song, allowing users to discover new music and artists.
-   **Permissions System:** DJ, administrator, and server owner permissions for different commands, allowing for more granular control over who can use each bot function.
-   **yt-dlp Integration:** Music downloads and playlist features for an enhanced playback experience.
-  **Asynchronous Download:** Music downloads occur in the background without blocking the bot.
-   **Activity Dashboard:** Web interface with `Streamlit` to monitor bot usage through detailed graphs, allowing administrators to understand how the bot is being utilized.
-   **Multi-Server Support:** The bot supports usage on multiple servers simultaneously.
-   **Bot Presence:** The bot indicates the number of connected servers and the help command in the status.
-   **Command Logs:** Records commands and errors in CSV files to assist with analysis and debugging.

## Project Structure


### File Descriptions

-   **`.gitignore`:** Defines files and directories that should not be tracked by Git, such as configuration files, downloads, logs, and virtual environments.
-   **`fair_queue.py`:** Implements the logic to order the playback queue fairly, ensuring that all users have their music played. Prioritizes songs marked as `playnext` and distributes the rest equitably.
-   **`grafics.py`:** Creates an interactive dashboard with `Streamlit` to analyze bot usage, displaying graphs of commands per user, server, channel, total playback time, and activity over time.
-   **`playlist_extrator.py`:** Contains functions to extract titles, artists, and URLs of songs from YouTube and YouTube Music playlists using the `yt_dlp` library.
-   **`main.py`:** The main bot file. Contains all the logic for Discord commands, music playback, queue management, asynchronous download system, Discord events, permissions configuration, and the vote-to-skip system.
-   **`radio.py`:** Implements the radio feature, which creates automatic playlists based on a song using the YouTube Music API (`ytmusicapi`).
-   **`requirements.txt`:** Lists all the necessary project dependencies, making environment setup easier.
-   **`server_config_manager.py`:** Manages server-specific configurations, such as DJ roles, queue settings, and other parameters, storing data in a JSON file for persistence.
-   **`utils.py`:** Contains utility functions to extract song titles from YouTube links or search terms, calculate progress bars for display in Discord, and obtain thumbnail URLs from YouTube videos.

## Detailed Features

### `fair_queue.py`

-   **`order_list(lista)`:**
    -   Orders a list of dictionaries (songs) based on two criteria:
        1.  Prioritizes songs with the `'playnext'` key set to `True`.
        2.  Then, distributes the remaining songs fairly among the users who added them, alternating between users.
    -   Uses `pandas` to facilitate data manipulation of the queue.

### `grafics.py`

-   Creates a `Streamlit` dashboard to display detailed information about bot activity:
    -   **General Summary:** Displays the total number of commands registered for the selected date.
    -   **Most Used Commands:** Presents a bar chart showing the frequency of usage for each command.
    -   **Activity per Server:** Displays a pie chart showing the distribution of commands per server and total playback time.
    -   **Activity per Channel:** Presents a bar chart showing the distribution of commands per channel.
    -   **Activity Over Time:** Displays a line graph showing the distribution of commands by hour of the day.
-   Allows administrators to monitor bot usage and identify behavioral patterns.

### `playlist_extrator.py`

-   **`get_playlist_titles(playlist_url)`:**
    -   Extracts information from a YouTube or YouTube Music playlist, including:
        -   Song title.
        -   Artist name.
        -   Video URL.
    -   Returns a list of dictionaries containing this information.
    -   Uses `yt_dlp` to extract information efficiently.

### `main.py`

-   **Bot Commands:**
    -   **`play <song>` / `tocar <song>`:** Adds a song or playlist to the playback queue. Accepts YouTube URLs or search terms.
    -   **`radio <song>` / `autoplaylist <song>`:** Creates a radio (automatic playlist) based on a song, adding it to the queue.
    -   **`queue [page]` / `fila [page]`:** Displays the current playback queue, with pagination for long queues.
    -   **`nowplaying` / `tocandoagora` / `playingnow` / `agoratocando`:** Shows information about the currently playing song, including playback progress, the name of the user who added the song, and a thumbnail.
    -   **`shuffle` / `embaralhar`:** Shuffles the playback queue.
    -   **`remove <number>` / `remover <number>`:** Removes a specific song from the queue by its number, with permission from the user who added it or a DJ.
    -   **`help`:** Displays a list of all available commands and their descriptions.
    -   **`skip` / `pular`:** Votes to skip the current song. Requires a certain number of votes to skip, unless the user who added the song uses the command.
    -   **`forceskip`:** Forces the current song to be skipped immediately, only for DJs, administrators, and owners.
    -   **`clear` / `limpar`:** Clears the entire playback queue, only for DJs, administrators, and owners.
    -   **`stop` / `parar`:** Stops music playback and clears the queue, only for DJs, administrators, and owners.
    -   **`setdj <role>`:** Sets a role as DJ, allowing members with that role to use special bot commands (administrators and owners).
    -   **`removedj`:** Removes the previously set DJ role (administrators and owners).
    -   **`checkpermissao`:** Checks and displays the user's permissions on the bot.
    -   **`playnext <song>` / `tocaraseguir <song>`:** Adds a song to the top of the queue to be played next (DJ and Admin).
    -   **`move <from_index> <to_index>` / `mover <from_index> <to_index>`:** Moves a song's position in the queue. Requires the user to be the original song adder, or a DJ and Admin.
    -   **`resume`:** Resumes paused music playback.
-   **Bot Events:**
    -   **`on_ready()`:** Executed when the bot is ready, loading server information, members, and initiating asynchronous tasks.
    -   **`on_guild_join(guild)`:** Triggered when the bot joins a new server, registering the server and configuring its initial settings.
    -   **`on_guild_remove(guild)`:** Triggered when the bot is removed from a server, recording the event for future analysis.
    -   **`on_command(ctx)`:** Triggered when a command is executed, recording command information in a CSV file for monitoring and analysis.
    -   **`on_command_error(ctx, error)`:** Triggered when an error occurs while executing a command, recording error details for debugging.
-   **Playback Logic:**
    -   Uses `yt_dlp` to download audio files from YouTube.
    -   Plays audio files using `discord.FFmpegOpusAudio`.
    -   Manages a playback queue per server, with an asynchronous download system using `asyncio.to_thread`.
    -   Vote-to-skip system, with the number of votes based on the number of listeners.
    -   Monitors song progress in real-time and displays the progress bar in Discord.
-   **Auxiliary Functions:**
    -   **`servidor_e_canal_usuario(ctx)`:** Obtains the server ID and user's voice channel ID from the command context.
    -   **`permissao(ctx)`:** Checks the user's permissions based on their roles, server owner status, and bot owner status.
    -   **`tocar(ctx, filepath, voice_channel, server_id)`:** Plays the music in a specific voice channel.
    -   **`gatekeeper()`:** Asynchronous function that checks the queue of each server and starts downloading pending songs.
    -   **`gatekeeper_tocar()`:** Asynchronous function that starts the music playback loop for each server.
    -   **`processar_fila_servidor(server_id)`:** Function that manages music playback for each server.
    -  **`obter_tempo_musica(server_id)`:** Returns the current and total time of the music being played.
    -   **`pause(ctx)`:** Pauses the current song.
    -   **`resume(ctx)`:** Resumes paused music playback.

### `radio.py`

-   **`gerar_radio(nome_musica)`:**
    -   Searches for a song on YouTube Music using `ytmusicapi`.
    -   Extracts song information and generates a playlist of recommended songs.
    -   Returns the list of songs in the radio.

### `server_config_manager.py`

-   Manages server-specific configurations, storing them in a JSON file:
    -   **`load_servers(filepath)`:** Loads server configurations from a JSON file.
    -   **`save_servers(servers, filepath)`:** Saves server configurations to a JSON file.
    -   **`add_server(servers, server_id)`:** Adds a new server with default settings.
    -   **`update_server(servers, server_id, **kwargs)`:** Updates the settings of a specific server.
    -   **`remove_server(servers, server_id)`:** Removes the settings of a specific server.

### `utils.py`

-   **`obter_titulo(input)`:**
    -   Extracts the title and artist of a song from a YouTube URL or a search term.
    -   Uses `ytmusicapi` to get information about the song.
-   **`calcular_barra_progresso(tempo_atual, duracao_total, comprimento_barra=20)`:** Generates a text progress bar for display in Discord, showing the current progress of a song.
-   **`get_thumbnail_url(video_url)`:** Extracts the ID of a YouTube video and returns the corresponding thumbnail URL.

## How to Run

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/jataemuso/capymusictron.git
    cd capymusictron
    ```
2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # venv\Scripts\activate  # On Windows
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure environment variables:**
    -   Create a `.env` file in the root of the project.
    -   Add your bot token, prefix, and bot owner ID:
        ```env
        DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
        BOT_PREFIX=!
        BOT_OWNER_ID=YOUR_BOT_OWNER_ID_HERE
        ```
5.  **Run the bot:**
    ```bash
    python quee.py
    ```
6.  **Run the dashboard:**
   ```bash
    streamlit run grafics.py
   ```

## Contributing

Contributions are welcome! If you wish to contribute to the project, follow these steps:

1.  Fork the repository.
2.  Create a branch for your feature (`git checkout -b feature/YourFeature`).
3.  Make your changes and commit (`git commit -am 'Add new feature'`).
4.  Push to your branch (`git push origin feature/YourFeature`).
5.  Create a new Pull Request.
