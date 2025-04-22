from datetime import datetime
from flask import Flask, request, jsonify
from db import MongoDBManager
import joblib
import logging
import numpy as np
from flask_cors import CORS

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Carrega modelo, encoder e ordem de features
    try:
        app.model = joblib.load('models/obesity_rf_model.joblib')
        app.label_encoder = joblib.load('models/label_encoder.joblib')
        app.feature_order = joblib.load('models/features_order.joblib')
    except Exception as e:
        logger.error(f"Erro ao carregar modelo: {e}")
        raise
    
    # Inicializa MongoDB
    app.db_manager = MongoDBManager()

    def prepare_input(data):
        """Prepara os dados de entrada na ordem correta para o modelo"""
        return np.array([
            int(data['Age']),
            1 if data['Gender'] == 'Male' else 0,
            float(data['Height']),
            float(data['Weight']),
            int(data['FAF']),
            1 if data['SMOKE'].lower() == 'yes' else 0,
            1 if data['FAVC'].lower() == 'yes' else 0,
            1 if data['family_history_with_overweight'].lower() == 'yes' else 0,
            {'Never': 0, 'Sometimes': 1, 'Frequently': 2, 'Always': 3}[data['CAEC']],
            {'Never': 0, 'Sometimes': 1, 'Frequently': 2, 'Always': 3}[data['CALC']],
            {
                'Automobile': 0, 
                'Bike': 1, 
                'Motorbike': 2, 
                'Public_Transportation': 3, 
                'Walking': 4
            }[data['MTRANS']]
        ]).reshape(1, -1)

    @app.route('/predict', methods=['POST'])
    def predict():
        """Endpoint para predição de obesidade"""
        try:
            data = request.get_json()
            
            # Validação dos campos obrigatórios
            required_fields = app.feature_order + ['CAEC', 'CALC', 'MTRANS']
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Campo obrigatório faltando: {field}"}), 400
            
            # Validações específicas
            if not (14 <= int(data['Age']) <= 100):
                return jsonify({"error": "Idade deve estar entre 14 e 100 anos"}), 400
                
            if not (1.4 <= float(data['Height']) <= 2.2):
                return jsonify({"error": "Altura inválida (deve ser entre 1.4m e 2.2m)"}), 400
                
            if not (40 <= float(data['Weight']) <= 200):
                return jsonify({"error": "Peso inválido (deve ser entre 40kg e 200kg)"}), 400
                
            if int(data['FAF']) not in [0, 1, 2, 3]:
                return jsonify({"error": "Frequência de atividade física deve ser 0-3"}), 400

            # Pré-processamento
            try:
                features = prepare_input(data)
            except KeyError as e:
                return jsonify({"error": f"Valor inválido em: {str(e)}"}), 400
            except ValueError as e:
                return jsonify({"error": f"Valor numérico inválido: {str(e)}"}), 400
            
            # Predição
            prediction = app.model.predict(features)[0]
            prediction_label = app.label_encoder.inverse_transform([prediction])[0]
            
            # Salvar no MongoDB
            prediction_data = {
                **data,
                "processed_features": {k: v for k, v in zip(app.feature_order, features[0])},
                "prediction": prediction_label,
                "prediction_date": datetime.now()
            }
            
            prediction_id = app.db_manager.save_prediction(prediction_data)
            
            return jsonify({
                "prediction": prediction_label,
                "prediction_id": str(prediction_id),
                "features_used": app.feature_order
            })
        except Exception as e:
            logger.error(f"Erro na predição: {str(e)}", exc_info=True)
            return jsonify({"error": "Erro interno no processamento"}), 500

    @app.route('/predictions', methods=['GET'])
    def list_predictions():
        """Endpoint para listar predições históricas"""
        try:
            # Garante que a conexão está ativa
            if not app.db_manager.client:
                app.db_manager._connect()
                
            predictions = app.db_manager.get_predictions(limit=100)
            
            # Converter ObjectId para strings e remover campos sensíveis
            safe_predictions = []
            for pred in predictions:
                pred['_id'] = str(pred['_id'])
                if 'processed_features' in pred:
                    del pred['processed_features']
                safe_predictions.append(pred)
                
            return jsonify(safe_predictions)
        except Exception as e:
            logger.error(f"Erro ao recuperar predições: {str(e)}")
            return jsonify({"error": "Erro ao recuperar histórico"}), 500
        

    @app.route('/total_predictions', methods=['GET'])
    def total_predictions():
        try:
            if not app.db_manager.client:
                app.db_manager._connect()
            total = app.db_manager.db.predictions.count_documents({})
            return jsonify({'total_predictions': total})
        except Exception as e:
            logger.error(f"Erro ao contar previsões: {str(e)}")
            return jsonify({'error': str(e)}), 500


    @app.route('/features', methods=['GET'])
    def get_features_info():
        """Endpoint para obter informações sobre as features esperadas"""
        feature_info = {
            "feature_order": app.feature_order,
            "required_fields": {
                "Age": {"type": "integer", "min": 14, "max": 100},
                "Gender": {"type": "string", "values": ["Male", "Female"]},
                "Height": {"type": "float", "min": 1.4, "max": 2.2, "unit": "meters"},
                "Weight": {"type": "float", "min": 40, "max": 200, "unit": "kg"},
                "FAF": {"type": "integer", "min": 0, "max": 3, "description": "0=Nenhuma, 1=1-2 dias, 2=3-4 dias, 3=5+ dias"},
                "SMOKE": {"type": "string", "values": ["yes", "no"]},
                "FAVC": {"type": "string", "values": ["yes", "no"]},
                "family_history_with_overweight": {"type": "string", "values": ["yes", "no"]},
                "CAEC": {"type": "string", "values": ["Never", "Sometimes", "Frequently", "Always"]},
                "CALC": {"type": "string", "values": ["Never", "Sometimes", "Frequently", "Always"]},
                "MTRANS": {"type": "string", "values": ["Automobile", "Bike", "Motorbike", "Public_Transportation", "Walking"]}
            }
        }
        return jsonify(feature_info)

    @app.route('/predictions/distribution', methods=['GET'])
    def prediction_distribution():
        """Endpoint para distribuição das classes de obesidade"""
        try:
            if not app.db_manager.client:
                app.db_manager._connect()
            
            pipeline = [
                {"$group": {"_id": "$prediction", "count": {"$sum": 1}}}
            ]
            
            results = list(app.db_manager.db.predictions.aggregate(pipeline))
            
            distribution = {item['_id']: item['count'] for item in results}
            
            # Garante que todas as classes possíveis estão presentes
            all_classes = ['Insufficient_Weight', 'Normal_Weight', 'Overweight_Level_I', 
                        'Overweight_Level_II', 'Obesity_Type_I', 'Obesity_Type_II', 'Obesity_Type_III']
            
            for cls in all_classes:
                if cls not in distribution:
                    distribution[cls] = 0
                    
            return jsonify(distribution)
        except Exception as e:
            logger.error(f"Erro ao calcular distribuição: {str(e)}")
            return jsonify({"error": "Erro ao calcular distribuição"}), 500

    @app.route('/predictions/gender-stats', methods=['GET'])
    def gender_statistics():
        """Estatísticas por gênero"""
        try:
            if not app.db_manager.client:
                app.db_manager._connect()
            
            pipeline = [
                {"$group": {
                    "_id": {"gender": "$Gender", "prediction": "$prediction"},
                    "count": {"$sum": 1}
                }}
            ]
            
            results = list(app.db_manager.db.predictions.aggregate(pipeline))
            
            # Processa os resultados para um formato mais amigável
            stats = {}
            for item in results:
                gender = item['_id']['gender']
                prediction = item['_id']['prediction']
                
                if gender not in stats:
                    stats[gender] = {}
                
                stats[gender][prediction] = item['count']
            
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas por gênero: {str(e)}")
            return jsonify({"error": "Erro ao calcular estatísticas por gênero"}), 500

    @app.route('/predictions/age-stats', methods=['GET'])
    def age_statistics():
        """Estatísticas por faixa etária"""
        try:
            if not app.db_manager.client:
                app.db_manager._connect()
            
            # Definimos os intervalos de idade desejados
            age_boundaries = [14, 20, 30, 40, 50, 60, 100]
            age_labels = [
                "14-19", 
                "20-29", 
                "30-39", 
                "40-49", 
                "50-59", 
                "60+"
            ]
            
            pipeline = [
                {"$bucket": {
                    "groupBy": "$Age",
                    "boundaries": age_boundaries,
                    "default": "60+",
                    "output": {
                        "count": {"$sum": 1},
                        "avg_weight": {"$avg": "$Weight"},
                        "predictions": {"$push": "$prediction"}
                    }
                }},
                {"$sort": {"_id": 1}}  # Ordena pelos intervalos de idade
            ]
            
            results = list(app.db_manager.db.predictions.aggregate(pipeline))
            
            # Processa os resultados para garantir todas as faixas são mostradas
            stats = []
            for i, item in enumerate(results):
                # Usamos o índice para pegar o label correto
                stats.append({
                    "age_range": age_labels[i],
                    "count": item['count'],
                    "avg_weight": round(float(item['avg_weight']), 1) if 'avg_weight' in item else 0,
                    "predictions": item['predictions']
                })
            
            # Garante que todas as faixas apareçam, mesmo com contagem zero
            if len(stats) < len(age_labels):
                existing_ranges = [s['age_range'] for s in stats]
                for i, label in enumerate(age_labels):
                    if label not in existing_ranges:
                        stats.insert(i, {
                            "age_range": label,
                            "count": 0,
                            "avg_weight": 0,
                            "predictions": []
                        })
            
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas por idade: {str(e)}")
            return jsonify({"error": "Erro ao calcular estatísticas por idade"}), 500



    @app.route('/predictions/activity-stats', methods=['GET'])
    def activity_statistics():
        """Estatísticas de atividade física vs peso"""
        try:
            if not app.db_manager.client:
                app.db_manager._connect()
            
            pipeline = [
                {
                    "$group": {
                        "_id": "$FAF",
                        "avg_weight": {"$avg": "$Weight"},
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"_id": 1}}
            ]
            
            results = list(app.db_manager.db.predictions.aggregate(pipeline))
            
            # Mapeia os níveis de atividade para labels mais amigáveis
            activity_labels = {
                0: "Sedentário",
                1: "Leve (1-2 dias)",
                2: "Moderado (3-4 dias)",
                3: "Ativo (5+ dias)"
            }
            
            stats = [{
                "activity_level": activity_labels.get(item["_id"]), 
                "avg_weight": round(float(item["avg_weight"])), 
                "count": item["count"]
            } for item in results]
            
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas de atividade: {str(e)}")
            return jsonify({"error": "Erro ao calcular estatísticas de atividade"}), 500



    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
