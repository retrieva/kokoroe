import logging

# Prevent "No handler found" warnings for library users who do not configure
# logging. CLI entry points should configure logging explicitly.
logging.getLogger(__name__).addHandler(logging.NullHandler())
