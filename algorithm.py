import datetime

def calculate_sm2(quality: int, repetitions: int, interval: int, e_factor: float):
    """
    Calculates the new repetition interval, repetition count, and E-Factor using the SM-2 algorithm.
    
    Args:
        quality (int): Performance rating (0-5). 
                       >= 3 means recalled. < 3 means forgotten.
        repetitions (int): Number of consecutive successful recalls.
        interval (int): Current interval in days.
        e_factor (float): Easiness factor.
    
    Returns:
        dict: {
            "interval": int (new interval in days),
            "repetitions": int,
            "e_factor": float
        }
    """
    if quality >= 3:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = int(interval * e_factor)
        
        repetitions += 1
    else:
        repetitions = 0
        interval = 1
    
    # Update E-Factor
    new_e_factor = e_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    
    # E-Factor cannot go below 1.3
    if new_e_factor < 1.3:
        new_e_factor = 1.3
        
    return {
        "interval": interval,
        "repetitions": repetitions,
        "e_factor": round(new_e_factor, 2)
    }

def get_next_review_date(last_reviewed: str, interval: int) -> str:
    """
    Calculates the next review date based on the interval.
    """
    last_date = datetime.datetime.fromisoformat(last_reviewed)
    next_date = last_date + datetime.timedelta(days=interval)
    return next_date.isoformat()
