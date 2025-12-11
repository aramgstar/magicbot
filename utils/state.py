user_states = {}      # user_id -> state string
user_sessions = {}    # user_id -> dict


def set_state(user_id, state):
    user_states[user_id] = state


def get_state(user_id):
    return user_states.get(user_id)


def clear_state(user_id):
    user_states.pop(user_id, None)


def get_session(user_id):
    return user_sessions.setdefault(user_id, {})


def save_session(user_id, data: dict):
    user_sessions[user_id] = data
