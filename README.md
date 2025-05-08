# KilljoyBot

KilljoyBot is a Telegram bot designed for content moderation using a two-stage AI evaluation system. It leverages LangChain and OpenAI models (via OpenRouter) to flag potentially problematic messages and determine appropriate actions.

## Features

- **Two-Stage Evaluation:** Messages are first flagged by a WardenAI model and then assessed for severity and action by a JudgmentAI model.
- **Telegram Integration:** Connects to the Telegram API to receive and respond to messages.
- **Database Integration:** Uses Tortoise ORM to store user information and suspicious messages.
- **Configurable AI Models:** Uses OpenRouter to access various models, currently configured for `google/gemini-2.0-flash-001`.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd KilljoyBot
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create a `.env` file:**
    Create a file named `.env` in the project root and add the following environment variables:

    ```dotenv
    BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
    OPENROUTER_KEY=YOUR_OPENROUTER_API_KEY
    DB_CONNECTION=sqlite://data/db.sqlite
    ```

    -   `YOUR_TELEGRAM_BOT_TOKEN`: Obtain this from the BotFather on Telegram.
    -   `YOUR_OPENROUTER_API_KEY`: Obtain this from OpenRouter.ai.
    -   `DB_CONNECTION`: The connection string for your database. The example uses a local SQLite database.

5.  **Initialize the database:**
    The database schema will be generated automatically when the application starts for the first time.

## Running the Bot

To start the bot, run the `main.py` file:

```bash
python main.py
```

The bot will connect to Telegram and start processing messages in the configured chat.

## Project Structure

-   `clients/`: Contains client implementations for external services (e.g., OpenAI via OpenRouter).
-   `database/`: Contains database models and initialization logic using Tortoise ORM.
-   `evaluation/`: Contains the AI evaluation logic, including prompts and LangChain graph setup.
-   `telegram/`: Contains the Telegram bot implementation using `aiogram`.
-   `warden/`: The main application logic orchestrating the different components.
-   `main.py`: The entry point for the application.
-   `requirements.txt`: Project dependencies.
-   `.env.example`: An example environment file (you need to create `.env`).

## Contributing

(Add contributing guidelines here if applicable)

## License

(Add license information here)
