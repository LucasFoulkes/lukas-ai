import random

def nick_generator() -> str:
    """
    Generate a random nickname by combining an adjective with a canine name.
    
    Returns:
        str: A generated nickname consisting of a randomly selected adjective and canine name.
    """
    canines = [
        'dog', 'wolf', 'fox', 'husky', 'beagle', 'poodle', 'collie', 'terrier',
        'coyote', 'jackal', 'dingo', 'rottweiler', 'mastiff', 'greyhound', 'whippet',
        'dalmatian', 'chihuahua', 'pomeranian', 'sheepdog', 'bulldog'
    ]
    
    adjectives = [
        'happy', 'silly', 'brave', 'calm', 'cool', 'chill', 'merry', 'kind',
        'fierce', 'shy', 'excited', 'jolly', 'cheerful', 'lazy', 'sleepy', 
        'hungry', 'friendly', 'wild', 'gentle', 'energetic'
    ]

    # Randomly select an adjective and a canine name
    adjective = random.choice(adjectives)
    canine = random.choice(canines)

    return f"{adjective}_{canine}"

