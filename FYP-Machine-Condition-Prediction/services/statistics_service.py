# services/statistics_service.py

import numpy as np

class StatisticsService:

    @staticmethod
 
    def compute_hourly_mean(data_points):
        if not data_points:
            return None

        
        current_values = [p['current'] for p in data_points]
        accX_values = [p['accX'] for p in data_points]
        accY_values = [p['accY'] for p in data_points]
        accZ_values = [p['accZ'] for p in data_points]
        tempA_values = [p['tempA'] for p in data_points]
        tempB_values = [p['tempB'] for p in data_points]

    
        mean_values = {
            "current_mean": round(np.mean(current_values), 3),
            "accX_mean": round(np.mean(accX_values), 3),
            "accY_mean": round(np.mean(accY_values), 3),      # call the class StatisticsService.compute_hourly_mean(data_points) return mean_values
            "accZ_mean": round(np.mean(accZ_values), 3),        
            "tempA_mean": round(np.mean(tempA_values), 3),
            "tempB_mean": round(np.mean(tempB_values), 3),
            "num_points_used": len(data_points)
        }
        return mean_values




