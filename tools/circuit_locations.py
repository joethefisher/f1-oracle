"""
Static mapping from races.circuit (as stored in DB after setup_season normalization)
to (latitude, longitude) for weather lookups.
"""

CIRCUIT_LOCATIONS: dict[str, tuple[float, float]] = {
    # 2026 calendar
    "Melbourne":        (-37.8497,  144.9680),
    "Jeddah":           ( 21.6319,   39.1044),
    "Shanghai":         ( 31.3389,  121.2198),
    "Suzuka":           ( 34.8431,  136.5407),
    "Bahrain":          ( 26.0325,   50.5106),
    "Miami":            ( 25.9581,  -80.2389),
    "Imola":            ( 44.3439,   11.7167),
    "Monaco":           ( 43.7347,    7.4205),
    "Montreal":         ( 45.5048,  -73.5228),
    "Barcelona":        ( 41.5700,    2.2611),
    "Spielberg":        ( 47.2197,   14.7647),  # Red Bull Ring, Austria
    "Silverstone":      ( 52.0786,   -1.0169),
    "Budapest":         ( 47.5830,   19.2526),
    "Spa-Francorchamps": ( 50.4372,    5.9714),
    "Spa":              ( 50.4372,    5.9714),
    "Zandvoort":        ( 52.3888,    4.5409),
    "Monza":            ( 45.6156,    9.2811),
    "Baku":             ( 40.3725,   49.8533),
    "Singapore":        (  1.2914,  103.8640),
    "Austin":           ( 30.1328,  -97.6411),
    "Mexico City":      ( 19.4042,  -99.0907),
    "São Paulo":        (-23.7036,  -46.6997),
    "Sao Paulo":        (-23.7036,  -46.6997),
    "Las Vegas":        ( 36.1147, -115.1728),
    "Lusail":           ( 25.4900,   51.4542),
    "Losail":           ( 25.4900,   51.4542),
    "Abu Dhabi":        ( 24.4672,   54.6031),
    "Yas Island":       ( 24.4672,   54.6031),
    # Historic / alternate spellings
    "Sakhir":           ( 26.0325,   50.5106),
    "Portimão":         ( 37.2272,   -8.6268),
    "Mugello":          ( 43.9975,   11.3719),
    "Istanbul":         ( 40.9517,   29.4050),
    "Nürburgring":      ( 50.3356,    6.9475),
    "Bahrain International Circuit": (26.0325, 50.5106),
}
