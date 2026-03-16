from retrying import retry


def should_retry(exception):
    error_str = str(exception).lower()
    return 'throttl' in error_str or 'serviceunavailable' in error_str

@retry(retry_on_exception=should_retry,
       wait_fixed=5000,
       stop_max_delay=30*1000)
def call_with_retry(f):
    return f()