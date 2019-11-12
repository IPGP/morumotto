# -*- coding: utf-8 -*-
import sys
import inspect
import importlib
# import pyclbr
from plugins import structure, source, format, metadata_format


def get_plugin_choices(name):
    """
    This is simply a method which reads a module given by name and returns
    a tuple of choices which are all class found in the given module
    """

    # Better option than what we did now
    # The problem is that it is not working for now with python > 3.7...
    # If bug is fixed, simply use the following 3 lines instead of lines 39
    # to 44

    # for cls in pyclbr.readmodule(module_name):
    #     if cls != abstract_class:
    #         CHOICES += ((cls,cls),)

    CHOICES = ()
    if name == "source":
        module_name = "plugins.source"
        abstract_class = "SourcePlugin"
    elif name == "format":
        module_name = "plugins.format"
        abstract_class = "DataFormat"
    elif name == "metadata_format":
        module_name = "plugins.metadata_format"
        abstract_class = "MetadataFormat"
    elif name == "structure":
        module_name = "plugins.structure"
        abstract_class = "AbstractStructure"
    else:
        return (("%s not implemented yet" % name))

    sources_class = [cls[0] for cls in
                     inspect.getmembers(sys.modules[module_name],
                                        inspect.isclass)
                     if cls[1].__module__ == sys.modules[module_name].__name__
                     and cls[0] != abstract_class]
    for cls in sources_class:
        CHOICES += ((cls,cls),)
    return CHOICES


def get_sources_templates():
    """
    This is simply a method which reads a module given by name and returns
    a tuple of choices which are all class found in the given module
    """

    # Better option than what we did now
    # The problem is that it is not working for now with python > 3.7...
    # If bug is fixed, simply use the following 3 lines instead of lines 39
    # to 44

    # for cls in pyclbr.readmodule(module_name):
    #     if cls != abstract_class:
    #         CHOICES += ((cls,cls),)

    TEMPLATES = dict()
    module_name = "plugins.source"
    abstract_class = "SourcePlugin"

    sources_class = [cls[0] for cls in
                     inspect.getmembers(sys.modules[module_name],
                                        inspect.isclass)
                     if cls[1].__module__ == sys.modules[module_name].__name__
                     and cls[0] != abstract_class]
    for cls in sources_class:
        module = importlib.import_module("plugins.source")
        class_ = getattr(module, cls)

        TEMPLATES[cls] = class_().template
    return TEMPLATES
