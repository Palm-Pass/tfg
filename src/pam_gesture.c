#define PAM_SM_AUTH
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>
#include <syslog.h>

static const char *venv_root = "/usr/lib/howdy";
static const char *venv_python = "/usr/lib/howdy/.venv/bin/python3";
static const char *compare_script = "/usr/lib/howdy/compare.py";

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

/*
Custom PAM module for gesture-based authentication using a Python script.
 */
PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *user;
    int status;

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
        pam_syslog(pamh, LOG_ERR, "TFG-LOG: venv not found at /usr/lib/howdy/.venv");
        return PAM_AUTH_ERR;
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