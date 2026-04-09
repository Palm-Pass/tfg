#define PAM_SM_AUTH
#include <security/pam_modules.h>
#include <security/pam_ext.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/wait.h>
#include <syslog.h>

/*
Custom PAM module for gesture-based authentication using a Python script.
 */
PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *user;
    int status;

    // Get the username from PAM
    if (pam_get_user(pamh, &user, NULL) != PAM_SUCCESS) {
        return PAM_AUTH_ERR;
    }

    // Stablish paths to the Python executable and the compare.py script
    char *python_executable = "/usr/lib/howdy-gesture/.venv/bin/python";
    char *compare_script = "/usr/lib/howdy-gesture/src/compare.py";

    // Build the execution command with the environment variable for the user
    char command[512];
    snprintf(command, sizeof(command), "HOWDY_USER=%s %s %s %s", 
             user, python_executable, compare_script, user);

    status = system(command);

    
    if (status != -1 && WEXITSTATUS(status) == 0) {
        pam_syslog(pamh, LOG_INFO, "TFG-LOG: Autenticación exitosa para %s", user);
        return PAM_SUCCESS;
    }

    pam_syslog(pamh, LOG_ERR, "TFG-LOG: Autenticación fallida para %s", user);
    return PAM_AUTH_ERR;
}

PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}