from streamgui.app import App


def main() -> None:
    """Start the streamGUI application by creating and running the main App window."""
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
