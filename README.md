# RAG Chatbot with FastAPI and Next.js

A Retrieval-Augmented Generation (RAG) chatbot that allows users to upload documents and chat with an AI about their contents. Built with FastAPI, Next.js, SQLAlchemy, and Pinecone.

Demo: 

## Features

- 📁 Document upload support (PDF, DOCX, TXT)
- 💬 Real-time chat interface
- 🔍 RAG-powered responses using Pinecone
- 📱 Responsive design
- 🗄️ Chat history persistence

## Prerequisites

### Backend Requirements
- Python 3.11
- Supabase Database
- Pinecone Account
- OpenAI API Key

### Frontend Requirements
- Node.js 18+
- npm or yarn

## Environment Setup

1. Clone the repository:

git clone 
cd rag-chatbot

2. Create a `.env` file in the root directory with the following variables:

```
SUPABASE_DB=your_supabase_postgres_url (make sure to add +asyncpg example: postgresql+asyncpg://postgres.asdasdasdad:asdasdasdsd@aws-0-us-east-1.pooler.supabase.com:5432/postgres)
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
ENVIRONMENT= (either docker or local)


## Backend Setup

1. Create and activate a virtual environment:

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

2. Install backend dependencies:

pip install -r requirements.txt

3. Create the database tables:

python create_tables.py

4. Start the FastAPI server:

uvicorn main:app --reload

The backend API will be available at `http://localhost:8000` or `http://0.0.0.0:8000` if you are using Docker.

## Backend Setup with Docker

1. Build the Docker image:

docker-compose up --build

## Frontend Setup

1. Navigate to the frontend directory:

bash
cd frontend

2. Install frontend dependencies:

npm install or yarn install

3. Build the frontend:

npm run build or yarn build

4. Start the Next.js development server:

npm run start or yarn start

The frontend will be available at `http://localhost:3000` 
