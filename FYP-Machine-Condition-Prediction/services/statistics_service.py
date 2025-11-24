# services/statistics_service.py

import numpy as np

class StatisticsService:

    @staticmethod
    # def compute_hourly_mean(data):
    #     """
    #     Compute mean for each feature from 360 data points.
    #     Expects a list of dictionaries.
    #     """
    #     if len(data) == 0:
    #         return None

    #     temp_shaft = np.mean([d["temp_shaft"] for d in data])
    #     temp_body = np.mean([d["temp_body"] for d in data])
    #     current = np.mean([d["current"] for d in data])
    #     vibration = np.mean([d["vibration"] for d in data])

    #     return {
    #         "temp_shaft_mean": round(float(temp_shaft), 3),
    #         "temp_body_mean": round(float(temp_body), 3),
    #         "current_mean": round(float(current), 3),
    #         "vibration_mean": round(float(vibration), 3),
    #         "num_points_used": len(data)
    #     }
    def compute_hourly_mean(data_points):
        if not data_points:
            return None

        # Extract features using IOT field names
        current_values = [p['current'] for p in data_points]
        accX_values = [p['accX'] for p in data_points]
        accY_values = [p['accY'] for p in data_points]
        accZ_values = [p['accZ'] for p in data_points]
        tempA_values = [p['tempA'] for p in data_points]
        tempB_values = [p['tempB'] for p in data_points]

        # Compute means for all 6 features
        mean_values = {
            "current_mean": round(np.mean(current_values), 3),
            "accX_mean": round(np.mean(accX_values), 3),
            "accY_mean": round(np.mean(accY_values), 3),
            "accZ_mean": round(np.mean(accZ_values), 3),
            "tempA_mean": round(np.mean(tempA_values), 3),
            "tempB_mean": round(np.mean(tempB_values), 3),
            "num_points_used": len(data_points)
        }
        return mean_values




