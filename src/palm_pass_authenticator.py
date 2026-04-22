import howdy
import Config
import message_print

def main():
    printer = message_print.Printer()
    printer.print_msg("Initializing configuration")
    configReader = Config.Config(printer)
    configReader.load_config()
    printer.print_msg("Configuration initialized successfully")
        

if __name__ == "__main__":
        main()
    

