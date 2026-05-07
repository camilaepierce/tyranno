# Starting Development Server

Create a virtual environment:

Linux
python3 venv -m .venv

Activate:

Linux
source .venv/bin/activate

Install dependencies
pip install -r requirements.txt

Neon database setup

Run `npx neonctl@latest init` and accept the AI-guided setup so Neon creates a PostgreSQL connection string for this project. Put the generated `DATABASE_URL` into `.env`, then run Django migrations against that database.

python3 manage.py migrate

Site to streamline REX event submissions.

---------------------------------------------
Uses Django.

Built by DormCon Tech Chair.
