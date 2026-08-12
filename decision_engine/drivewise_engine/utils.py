def clamp(v, low=0.0, high=100.0):
    return max(low, min(high, float(v)))

def normalize_weights(weights):
    total = sum(weights.values()) or 1.0
    return {k: v / total for k, v in weights.items()}
