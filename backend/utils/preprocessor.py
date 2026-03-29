import numpy as np

def preprocess_input(at, v, ap, rh):
    """
    Apply any necessary preprocessing to the input features.
    For now, it just returns them as a numpy array.
    If the model was trained with scaling (e.g., StandardScaler),
    scaling parameters should be applied here.
    """
    return np.array([[at, v, ap, rh]], dtype=np.float32)
