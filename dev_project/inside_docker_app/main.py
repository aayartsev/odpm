try:
    from .container_bootstrap import main
except ImportError:
    from container_bootstrap import main

if __name__ == "__main__":
    main()
