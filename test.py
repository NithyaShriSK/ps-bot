from app import answer_question

def main():
    print("Student Skills Query Test")
    print("Type a question, or type 'exit' to quit.")
    test_user_id = "LOCAL_TEST_USER"

    while True:
        question = input("\nQuestion: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        try:
            print(f"\nAnswer:\n{answer_question(test_user_id, question)}")
        except Exception as error:
            print(f"\nRequest failed: {type(error).__name__}: {error}")

if __name__ == "__main__":
    main()