#define PAM_SM_AUTH
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>
#include <syslog.h>
#include <string.h>

static const char *venv_python = "/usr/lib/howdy/.venv/bin/python3";
static const char *compare_script = "/usr/lib/howdy/compare-gesture.py";

static int uv_is_installed(void) {
    return access("/usr/bin/uv", X_OK) == 0;
}

static int venv_exists(void) {
    return access(venv_python, X_OK) == 0;
}

static int run_compare(const char *user) {
    int status;
    pid_t pid = fork();

    if (pid == -1) {
        return -1;
    }

    if (pid == 0) {
        execl(venv_python, venv_python, compare_script, user, (char *)NULL);
        _exit(127);
    }

    if (waitpid(pid, &status, 0) == -1) {
        return -1;
    }

    return status;
}

static int get_gesture_hint_message(char *buffer, size_t buffer_size) {
    int pipefd[2];
    pid_t pid;
    int status;
    ssize_t bytes_read;

    if (pipe(pipefd) == -1) {
        return -1;
    }

    pid = fork();
    if (pid == -1) {
        close(pipefd[0]);
        close(pipefd[1]);
        return -1;
    }

    if (pid == 0) {
        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO);
        close(pipefd[1]);
        execl(venv_python, venv_python, "-c",
              "import sys; sys.path.insert(0, '/usr/lib/howdy'); "
              "from palm_pass_hints import get_gesture_hint_string; "
              "print(get_gesture_hint_string())",
              (char *)NULL);
        _exit(127);
    }

    close(pipefd[1]);
    bytes_read = read(pipefd[0], buffer, buffer_size - 1);
    close(pipefd[0]);

    if (waitpid(pid, &status, 0) == -1) {
        return -1;
    }

    if (bytes_read > 0) {
        buffer[bytes_read] = '\0';
        if (buffer[bytes_read - 1] == '\n') {
            buffer[bytes_read - 1] = '\0';
        }
        return 0;
    }

    return -1;
}

/*
Custom PAM module for gesture-based authentication using a Python script.
 */
PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *user;
    int status;
    char gesture_hint[256];

    (void)flags;
    (void)argc;
    (void)argv;

    if (pam_get_user(pamh, &user, NULL) != PAM_SUCCESS) {
        return PAM_AUTH_ERR;
    }

    if (!uv_is_installed()) {
        pam_syslog(pamh, LOG_ERR, "TFG-LOG: uv is not installed at /usr/bin/uv");
        return PAM_AUTH_ERR;
    }

    if (!venv_exists()) {
        pam_syslog(pamh, LOG_ERR, "TFG-LOG: venv not found at /lib/security/howdy/.venv");
        return PAM_AUTH_ERR;
    }

    /* Get and display gesture hint message */
    if (get_gesture_hint_message(gesture_hint, sizeof(gesture_hint)) == 0) {
        pam_info(pamh, "Howdy TFG - %s", gesture_hint);
    } else {
        pam_info(pamh, "Howdy TFG - Gesture authentication required");
    }

    status = run_compare(user);
    if (status != -1 && WIFEXITED(status) && WEXITSTATUS(status) == 0) {
        pam_syslog(pamh, LOG_INFO, "TFG-LOG: compare.py returned success for %s", user);
        return PAM_SUCCESS;
    }

    pam_syslog(pamh, LOG_ERR, "TFG-LOG: compare.py returned failure for %s", user);
    return PAM_AUTH_ERR;
}

PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}
