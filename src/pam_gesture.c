#define PAM_SM_AUTH
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <syslog.h>

static const char *default_root = "/usr/lib/howdy-gesture";
static const char *required_python_version = "3.10.19";

static const char *get_project_root(void) {
    const char *root = getenv("HOWDY_GESTURE_ROOT");
    if (root == NULL || root[0] == '\0') {
        return default_root;
    }
    return root;
}

static const char *select_python_executable(const char *project_root) {
    static char bundled_python[512];

    snprintf(bundled_python, sizeof(bundled_python), "%s/.venv/bin/python", project_root);
    if (access(bundled_python, X_OK) == 0) {
        return bundled_python;
    }

    if (access("/usr/bin/python3.10", X_OK) == 0) {
        return "/usr/bin/python3.10";
    }

    if (access("/usr/bin/python3", X_OK) == 0) {
        return "/usr/bin/python3";
    }

    return NULL;
}

static int python_is_required_version(const char *python_executable) {
    int status;
    pid_t pid = fork();

    if (pid == -1) {
        return 0;
    }

    if (pid == 0) {
        execl(
            python_executable,
            python_executable,
            "-c",
            "import platform,sys;sys.exit(0 if platform.python_version() == '3.10.19' else 1)",
            (char *)NULL
        );
        _exit(127);
    }

    if (waitpid(pid, &status, 0) == -1) {
        return 0;
    }

    return WIFEXITED(status) && WEXITSTATUS(status) == 0;
}

static int run_compare(const char *python_executable, const char *compare_script, const char *user) {
    int status;
    pid_t pid = fork();

    if (pid == -1) {
        return -1;
    }

    if (pid == 0) {
        setenv("HOWDY_USER", user, 1);
        execl(python_executable, python_executable, compare_script, user, (char *)NULL);
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
    const char *project_root;
    const char *python_executable;
    char compare_script[512];
    int status;

    // Get the username from PAM
    if (pam_get_user(pamh, &user, NULL) != PAM_SUCCESS) {
        return PAM_AUTH_ERR;
    }

    project_root = get_project_root();
    python_executable = select_python_executable(project_root);

    if (python_executable == NULL) {
        pam_syslog(pamh, LOG_ERR, "TFG-LOG: Python executable not found");
        return PAM_AUTH_ERR;
    }

    if (!python_is_required_version(python_executable)) {
        pam_syslog(
            pamh,
            LOG_ERR,
            "TFG-LOG: Python %s is required for dependencies, detected executable: %s",
            required_python_version,
            python_executable
        );
        return PAM_AUTH_ERR;
    }

    snprintf(compare_script, sizeof(compare_script), "%s/src/compare.py", project_root);
    status = run_compare(python_executable, compare_script, user);
    pam_syslog(pamh, LOG_INFO, "TFG-LOG: Executed compare.py with status %d", status);
    
    if (status != -1 && WIFEXITED(status) && WEXITSTATUS(status) == 0) {
        pam_syslog(pamh, LOG_INFO, "TFG-LOG: Successful authentication for %s", user);
        return PAM_SUCCESS;
    }

    pam_syslog(pamh, LOG_ERR, "TFG-LOG: Missed authentication for %s", user);
    return PAM_AUTH_ERR;
}

PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}