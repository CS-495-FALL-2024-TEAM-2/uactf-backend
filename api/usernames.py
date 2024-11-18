from passwords import generate_password

def generate_username(first_name: str, last_name: str = ""):
    full_name: str = first_name+last_name
    random_add_on: str = generate_password(7)
    username: str = f"{full_name}_{random_add_on}"
    return username
