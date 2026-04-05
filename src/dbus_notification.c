#include <stdio.h>
#include <stdlib.h>
#include <dbus/dbus.h>

void send_notification(const char* body_msg) {
    DBusError err;
    DBusConnection* conn;
    DBusMessage* msg;
    DBusMessageIter iter, arr_iter;
    DBusPendingCall* pending; // Para esperar al bus

    const char *app_name = "gnome-shell";
    dbus_uint32_t replaces_id = 0;
    const char *app_icon = "security-high";
    const char *summary = "Howdy TFG";
    int timeout = 5000;

    dbus_error_init(&err);
    conn = dbus_bus_get(DBUS_BUS_SESSION, &err);
    
    if (dbus_error_is_set(&err)) {
        fprintf(stderr, "Error de Bus: %s\n", err.message);
        dbus_error_free(&err);
        return;
    }

    msg = dbus_message_new_method_call("org.freedesktop.Notifications", 
                                       "/org/freedesktop/Notifications", 
                                       "org.freedesktop.Notifications", 
                                       "Notify");

    dbus_message_iter_init_append(msg, &iter);
    dbus_message_iter_append_basic(&iter, DBUS_TYPE_STRING, &app_name);
    dbus_message_iter_append_basic(&iter, DBUS_TYPE_UINT32, &replaces_id);
    dbus_message_iter_append_basic(&iter, DBUS_TYPE_STRING, &app_icon);
    dbus_message_iter_append_basic(&iter, DBUS_TYPE_STRING, &summary);
    dbus_message_iter_append_basic(&iter, DBUS_TYPE_STRING, &body_msg);

    dbus_message_iter_open_container(&iter, DBUS_TYPE_ARRAY, "s", &arr_iter);
    dbus_message_iter_close_container(&iter, &arr_iter);
    dbus_message_iter_open_container(&iter, DBUS_TYPE_ARRAY, "{sv}", &arr_iter);
    dbus_message_iter_close_container(&iter, &arr_iter);

    dbus_message_iter_append_basic(&iter, DBUS_TYPE_INT32, &timeout);

    // --- CAMBIO CRÍTICO AQUÍ ---
    // En lugar de dbus_connection_send, usamos send_with_reply_and_block
    // Esto obliga al programa a esperar a que el mensaje REALMENTE se envíe.
    DBusMessage* reply = dbus_connection_send_with_reply_and_block(conn, msg, 1000, &err);

    if (dbus_error_is_set(&err)) {
        fprintf(stderr, "Error al enviar: %s\n", err.message);
        dbus_error_free(&err);
    } else if (reply) {
        printf("Notificación aceptada por el bus.\n");
        dbus_message_unref(reply);
    }

    dbus_message_unref(msg);
    // No cerramos la conexión bruscamente, dejamos que el OS limpie
}

int main(int argc, char** argv) {
    if (argc < 2) return 0;
    send_notification(argv[1]);
    return 0;
}