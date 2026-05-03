from datetime import date


def main():
    name = input("What is your name? ").strip()
    age_text = input("How old are you? ").strip()

    if not name:
        name = "friend"

    try:
        age = int(age_text)
    except ValueError:
        print("Please enter your age as a whole number.")
        return

    if age < 0:
        print("Age cannot be negative.")
        return

    current_year = date.today().year
    year_turn_100 = current_year + (100 - age)

    print(f"Hello, {name}!")
    print(f"You will turn 100 in the year {year_turn_100}.")


if __name__ == "__main__":
    main()
