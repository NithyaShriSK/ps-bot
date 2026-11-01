from app import answer_question


def main():
    print("Student Skills Query Test")
    print("Type a question, or type 'exit' to quit.")

    while True:
        question = input("\nQuestion: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        try:
            print(f"\nAnswer: {answer_question(question)}")
        except Exception as error:
            print(f"\nRequest failed: {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
