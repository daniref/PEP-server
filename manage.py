#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import django
from django.conf import settings
from django.core.signals import request_finished
from django.dispatch import receiver
import multiprocessing
import threading

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')

    try:
        django.setup()    
        import core.handlers.hdl_registration as reg
        import core.handlers.hdl_commands as com
        import core.handlers.hdl_pendigexps as pen    
        import core.power.power as pow
        
        pow.PowerUpBoards()

        threadReg = threading.Thread(target=reg.RegisterDevices,args=())
        threadReg.daemon = True
        threadReg.start() 
        
        threadCommand = threading.Thread(target=com.HandlerCommands,args=())
        threadCommand.daemon = True
        threadCommand.start()

        threadRetrievePendingExp = threading.Thread(target=pen.RetrievePendingExps,args=())
        threadRetrievePendingExp.daemon = True
        threadRetrievePendingExp.start()
        
        from django.core.management import execute_from_command_line

    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
