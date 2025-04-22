from pymongo import MongoClient
from datetime import datetime
import os
from pymongo.errors import ConnectionFailure, PyMongoError
from dotenv import load_dotenv
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

class MongoDBManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self._connect()

    def _connect(self):
        """Estabelece conexão com o MongoDB."""
        try:
            # Obter URI de variável de ambiente
            MONGO_URI = os.getenv("MONGO_URI")
            if not MONGO_URI:
                raise ValueError("URI do MongoDB não configurada")
                
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.db = self.client["obesity_predictions"]
            self.collection = self.db["predictions"]
            
            # Testa a conexão
            self.client.admin.command('ping')
            logger.info("Conexão com MongoDB estabelecida com sucesso")
            
        except ConnectionFailure as e:
            logger.error(f"Falha ao conectar ao MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            raise

    def save_prediction(self, data):
        """Salva uma predição no MongoDB."""
        try:
            prediction_data = {
                **data,
                "prediction_date": datetime.now()
            }
            result = self.collection.insert_one(prediction_data)
            logger.info(f"Predição salva com ID: {result.inserted_id}")
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.error(f"Erro ao salvar predição: {e}")
            raise

    def get_predictions(self, limit=100):
        """Retorna as predições armazenadas."""
        try:
            return list(self.collection.find().sort("prediction_date", -1).limit(limit))
        except PyMongoError as e:
            logger.error(f"Erro ao recuperar predições: {e}")
            raise

    def close_connection(self):
        """Fecha a conexão com o MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Conexão com MongoDB encerrada")

# Exemplo de uso:
# db_manager = MongoDBManager()
# db_manager.save_prediction(data, prediction)
# predictions = db_manager.get_predictions()
# db_manager.close_connection()