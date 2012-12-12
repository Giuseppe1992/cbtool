#!/usr/bin/env python

#/*******************************************************************************
# Copyright (c) 2012 IBM Corp.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#/*******************************************************************************

'''
    Created on Nov 17, 2011

    Passive Object Operations Library

    @author: Marcio A. Silva, Michael R. Hines
'''
from os import chmod, makedirs
from os.path import isdir
from time import asctime, localtime, sleep, time
from random import randint
from subprocess import Popen, PIPE
from uuid import uuid5, NAMESPACE_DNS
from fileinput import FileInput
import copy

from lib.auxiliary.code_instrumentation import trace, cblog, cbdebug, cberr, cbwarn, cbinfo, cbcrit
from lib.auxiliary.value_generation import ValueGeneration
from lib.remote.process_management import ProcessManagement
from lib.auxiliary.data_ops import str2dic, dic2str, makeTimestamp
from lib.operations.base_operations import BaseObjectOperations

class PassiveObjectOperations(BaseObjectOperations) :
    
    @trace
    def list_objects(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _result = []
            _fmsg = "An error has occurred, but no error message was captured"
            _translation_cache = {}
            _fmt_obj_list = "No objects available."
            _obj_type = command.split('-')[0].upper()
            _obj_list = []
            _total = 0

            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

                if not _status and (obj_attr_list["state"].lower() not in ["pending", "failed", "finished"]):
                    if "limit" in obj_attr_list and obj_attr_list["limit"] != "none" :
                        _limit = int(obj_attr_list["limit"])
                    else:
                        _limit = 0
    
                    if _obj_type == "CLOUD" :
                        _obj_inst = self.pid
                        _fields = []
                        _fields.append("|name                    ")
                        _fields.append("|model                   ")
                        _fields.append("|description             ")
                    
                    elif _obj_type == "VMC" :
                        _fields = []
                        _fields.append("|name                    ")
                        _fields.append("|host_count      ")
                        _fields.append("|pool                    ")
                        _fields.append("|cloud_hostname                  ")
                        _fields.append("|cloud_ip         ")        
    
                    elif _obj_type == "HOST" :
                        _fields = []
                        _fields.append("|name                          ")
                        _fields.append("|vmc_name            ")
                        _fields.append("|function                                          ")
                        _fields.append("|pool         ")
                        _fields.append("|cloud_hostname              ")
                        _fields.append("|cloud_ip        ")      
    
                    elif _obj_type == "VM" :
                        _fields = []
                        _fields.append("|name          ")
                        _fields.append("|role                ")
                        _fields.append("|size        ")
                        _fields.append("|cloud_ip        ")
                        _fields.append("|host_name                  ")
                        _fields.append("|vmc_pool            ")
                        _fields.append("|ai      ")
                        _fields.append("|aidrs      ")                    
                        _fields.append("|svm_stub_vmc     ")
                        _fields.append("|uuid")
            #            _fields.append("|uuid                                 ")
                    elif _obj_type == "SVM" :
                        _fields = []
                        _fields.append("|name          ")
                        _fields.append("|role                ")
                        _fields.append("|primary_name     ")
                        _fields.append("|vmc            ")
                        _fields.append("|ai      ")
                        _fields.append("|uuid")
            #            _fields.append("|uuid                                 ")
                    elif _obj_type == "AI" :
                        _fields = []
                        _fields.append("|name      ")
                        _fields.append("|type           ")
            #            _fields.append("|uuid                                 ")
                        _fields.append("|sut                                               ")
                        _fields.append("|cloud_ip        ")
                        _fields.append("|arrival        ")
                        _fields.append("|aidrs                                   ")
                        _fields.append("|uuid")
                    elif _obj_type == "AIDRS" :
                        _fields = []
                        _fields.append("|name                ")
                        _fields.append("|pattern                ")
            #            _fields.append("|uuid                                 ")
                        _fields.append("|type              ")
                    else :
                        _msg = "Unknown object: " + _obj_type
                        raise self.ObjectOperationException(_msg, 28)
            
                    _fmt_obj_list = ''.join(_fields) + '\n'
    
                    if _obj_type == "CLOUD" :
                        _obj_list = self.osci.get_object_list(obj_attr_list["cloud_name"], _obj_type)
                    else :
                        _obj_list = self.osci.query_by_view(obj_attr_list["cloud_name"], _obj_type, "BYUSERNAME", obj_attr_list["username"], "name", "all", False)
    
                    if _obj_list :
                        for _obj in _obj_list :
                            if _obj.count('|') :
                                _obj_uuid, _obj_name = _obj.split('|')
                            else :
                                _obj_uuid = _obj
                            _obj_attrs = self.osci.get_object(obj_attr_list["cloud_name"], _obj_type, False, _obj_uuid, False)
    
                            if _obj_type == "VM" or _obj_type == "AI" :
                                if obj_attr_list["state"]  != "all" : 
                                    _state = self.osci.get_object_state(obj_attr_list["cloud_name"], _obj_type, _obj_uuid)
                                    if _state != obj_attr_list["state"] :
                                        continue
                                
                            if _limit and _total == _limit :
                                break
                            
                            _total += 1
                            _result.append(_obj_attrs)
                                
                            for _field in _fields :
                                _af = _field[1:].strip()
                                if _af == "vmc" or \
                                (_af == "svm_stub_vmc" and _obj_attrs[_af] != "none") or \
                                (_af == "ai" and _obj_attrs[_af] != "none") or \
                                (_af == "aidrs" and _obj_attrs[_af] != "none") :
                                    _obj_name = self.fast_uuid_to_name(obj_attr_list["cloud_name"], _af.split("_")[-1].upper(), \
                                                                       _obj_attrs[_af], \
                                                                       _translation_cache)
                                    
                                    #Screen is too small, just show names.
                                    #User can then later type 'ailist' or 'aslist' or 'vmclist'
                                    #to discover the UUID that they are interested in
                                    #_display_value = _obj_attrs[_af] + ' (' + _obj_name + ')'
                                    _display_value = _obj_name
                                else :
                                    _display_value = str(_obj_attrs[_af])
                                _fmt_obj_list += ('|' + _display_value).ljust(len(_field))
                            _fmt_obj_list += '\n'
    
                    else :
                        _fmt_obj_list = "No objects available."

                if obj_attr_list["state"] == "pending" :
                    for obj in self.osci.get_list(obj_attr_list["cloud_name"], _obj_type, "PENDING", True) :
                        _obj_uuid, _obj_name = obj[0].split("|")
                        _result.append({"uuid" : _obj_uuid, "name" : _obj_name, "status" : "pending", 
                                        "tracking" : self.osci.pending_object_get(obj_attr_list["cloud_name"], _obj_type, _obj_uuid)})
                        
                for state in ["failed", "finished" ] :
                    if obj_attr_list["state"] != state :
                        continue
                    objs = self.osci.get_object_list(obj_attr_list["cloud_name"], state.upper() + "TRACKING" + _obj_type, True)
                    if not objs :
                        continue
                    for obj in objs :
                        _result.append(self.osci.get_object(obj_attr_list["cloud_name"], state.upper() + "TRACKING" + _obj_type, False, obj, False)) 
    
                _status = 0
            
            else :
                _fmt_obj_list = "No objects available."

        except self.ObjectOperationException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 2
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 24
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Unable to get object list: " + _fmsg
                cberr(_msg)
            else : 
                _msg = "The following " + _obj_type + "s are attached to this "
                _msg += "experiment (Cloud "
                _msg += obj_attr_list["cloud_name"]  + ") :\n" + _fmt_obj_list
                cbdebug(_msg)
                
            return self.package(_status, _msg, _result)
        
    @trace
    def show_object(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _obj_type = command.split('-')[0].upper()
            _result = {}

            obj_attr_list["cloud_name"] = "undefined"
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

                if not _status :

                    _obj_select_attribs = obj_attr_list["specified_attributes"].split(',')
         
                    _smsg = "The " + _obj_type + " object " + obj_attr_list["name"]
                    _smsg += ", attached to this experiment, has the "
                    _smsg += "following attributes (Cloud "
                    _smsg += obj_attr_list["cloud_name"] + ") :\n"
            
                    _fmsg = "Unable to get the attributes for the " + _obj_type 
                    _fmsg += " object (Cloud " + obj_attr_list["cloud_name"] + "): "
        
                    if _obj_type == "CLOUD" :
                        _obj_type = "GLOBAL"
                        _fields = []            
                        _fields.append("|attribute (GLOBAL object)        ")
                        _fields.append("|\"sub-attribute\" (key)          ")
                        _fields.append("|value                                ")
        
                        if _obj_select_attribs[0] == "all" :
                            _obj_ids = sorted(obj_attr_list["all"].replace("command,",'').split(','))
                        else :
                            _obj_ids = _obj_select_attribs
                        
                        _fmt_obj_attr_list = ''.join(_fields) + '\n'
        
                        for _obj_id in _obj_ids :
                            _obj_attribs = self.osci.get_object(obj_attr_list["cloud_name"], _obj_type, False, \
                                                                _obj_id, False)
                            
                            _result[_obj_id] = {}
    
                            for _attrib, _value in iter(sorted(_obj_attribs.iteritems())) :
                                _fmt_obj_attr_list += '|' + _obj_id.ljust(len(_fields[0]) - 1)
                                _fmt_obj_attr_list += '|' + _attrib.ljust(len(_fields[1]) - 1)
                                _fmt_obj_attr_list += '|' + _value.ljust(len(_fields[2]) - 1)
                                _fmt_obj_attr_list += '\n'
                                
                                '''
                                    This is a method of reverse-engineering the cloud attributes
                                    in a way that is displayable in group form on the GUI
                                    the same way it is ordered in the configuration file.
                                '''
                                if _obj_select_attribs[0] == "all" :
                                    components = _attrib.split("_", 1)
                                    if len(components) == 1 :
                                        prefix = _attrib
                                        suffix = None
                                    else :
                                        prefix, suffix = components 
                                    
                                    if prefix in _result[_obj_id] and isinstance(_result[_obj_id][prefix], list):
                                        _result[_obj_id][prefix].append((suffix, _value))
                                    elif suffix != None :
                                        _result[_obj_id][prefix] = [(suffix, _value)]
                                    else :
                                        _result[_obj_id][prefix] = _value
                                        
                            for prefix in _result[_obj_id] :
                                liste = _result[_obj_id][prefix]
                                if isinstance(liste, list) and len(liste) == 1 :
                                    _result[_obj_id][prefix + "_" + liste[0][0]] = liste[0][1]
                                    del _result[_obj_id][prefix]
                                
                            if _obj_select_attribs[0] != "all" :
                                _result = copy.deepcopy(_obj_attribs)
        
                    elif _obj_type == "VMC" or _obj_type == "VM" or _obj_type == "HOST" or \
                        _obj_type == "AI" or _obj_type == "AIDRS" or _obj_type == "SVM":
                        _fields = []            
                        _fields.append("|attribute (" + _obj_type + " object key)               ")
                        _fields.append("|value                                ")
    
                        _fmt_obj_attr_list = ''.join(_fields) + '\n'
                        _obj_attribs = self.osci.get_object(obj_attr_list["cloud_name"], _obj_type, True, \
                                                            obj_attr_list["name"], \
                                                            False)
                        _obj_attribs["state"] = self.osci.get_object_state(obj_attr_list["cloud_name"], _obj_type, _obj_attribs["uuid"])
    
                        for _attrib, _value in iter(sorted(_obj_attribs.iteritems())) :
                            if _attrib in _obj_select_attribs or \
                            _obj_select_attribs[0] == "all" :
                                _fmt_obj_attr_list += '|' + \
                                _attrib.ljust(len(_fields[0]) - 1)
                                _fmt_obj_attr_list += '|' + \
                                _value.ljust(len(_fields[1]) - 1)
                                _fmt_obj_attr_list += '\n'
                                
                        _result = copy.deepcopy(_obj_attribs)
                    else :
                        _msg = "Unknown object: " + _obj_type
                        raise self.ObjectOperationException(_msg, 28)            
        
                    _status = 0

        except self.ObjectOperationException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Unable to get the attributes for the " + _obj_type 
                _msg += " object (Cloud " + obj_attr_list["cloud_name"] + "): "
                _msg += _fmsg
                cberr(_msg)
            else :
                _msg = "The " + _obj_type + " object " + obj_attr_list["name"]
                _msg += ", attached to this experiment, has the "
                _msg += "following attributes (Cloud "
                _msg += obj_attr_list["cloud_name"] + ") :\n" + _fmt_obj_attr_list
                cbdebug(_msg)
            return self.package(_status, _msg, _result)

    @trace    
    def alter_object(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        _xfmsg = ""
        _fmsg = ""
        try :
            _status = 100
            _obj_type = command.split('-')[0].upper()
            _result = {}

            obj_attr_list["cloud_name"] = "undefined"
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

                if not _status :
                    _obj_attrib_kvs = []
                    
                    # Some values, themselves, can have commas, which should not be treated like additional
                    # keys, in which case we need to re-combine them into a single value.
                    # To do that, search for list entries that do not contain equal signs 
                    
                    for _suspected_kv in obj_attr_list["specified_kv_pairs"].split(',') :
                        if _suspected_kv.count("=") :
                            _obj_attrib_kvs.append(_suspected_kv)
                        else :
                            _obj_attrib_kvs[-1] += "," + _suspected_kv
    
                    _fields = [] 
    
                    if _obj_type == "CLOUD" :
                        _can_be_tag = False
                        _obj_type = "GLOBAL"
                        _obj_uuid = obj_attr_list["specified_attributes"]
    
                        _fields.append("|\"sub-attribute\" (key)                ")
                        _fields.append("|old value                          ")
                        _fields.append("|new value                          ")
    
                        _smsg = "The attribute \"" + obj_attr_list["specified_attributes"]
                        _smsg += "\" on Cloud " + obj_attr_list["cloud_name"] 
                        _smsg += " was modified:\n"
    
                        _fmsg = "Unable to change the \"sub-attributes\" " 
                        _fmsg += ','.join(_obj_attrib_kvs) + " part of the attribute \""
                        _fmsg += obj_attr_list["specified_attributes"] + "\" on Cloud " + obj_attr_list["cloud_name"] + ": "
    
                    else :
                        _can_be_tag = True
                        _obj_uuid = obj_attr_list["name"]
    
                        _fields.append("|attribute                              ")
                        _fields.append("|old value                          ")
                        _fields.append("|new value                          ")
    
                        _smsg = "The following attributes for the " + _obj_type
                        _smsg += " object were changed (Cloud " + obj_attr_list["cloud_name"] + "):\n"
    
                        _fmsg = "Unable to change the attributes " 
                        _fmsg += ','.join(_obj_attrib_kvs) + " for the " + _obj_type
                        _fmsg += " (Cloud " + obj_attr_list["cloud_name"] + ")."
    
                    _fmt_obj_chg_attr = ''.join(_fields) + '\n'
    
                    _old_values = self.osci.get_object(obj_attr_list["cloud_name"], _obj_type, _can_be_tag, \
                                                       _obj_uuid, False)

                    for _kv in _obj_attrib_kvs :
                        # use split('=', 1) to allow for value to contain
                        # equal signs themselves as a part of the value
                        _key, _value = _kv.split('=', 1)
    
                        if not _key in _old_values :
                            _old_values[_key] = "non-existent"
    
                        if _key[0] == '-' :
                            _key = _key[1:]
                            self.osci.remove_object_attribute(obj_attr_list["cloud_name"], _obj_type, _obj_uuid, \
                                                              _can_be_tag, _key)
                        else :
                            self.osci.update_object_attribute(obj_attr_list["cloud_name"], _obj_type, _obj_uuid, \
                                                              _can_be_tag, _key, _value)
                            
    
                        _fmt_obj_chg_attr += '|' + _key.ljust(len(_fields[0]) - 1)
                        _fmt_obj_chg_attr += '|' + _old_values[_key].ljust(len(_fields[1]) - 1)
                        _fmt_obj_chg_attr += '|' + _value.ljust(len(_fields[2]) - 1)
                        _result["old_" + _key] = _old_values[_key]
                        _result[_key] = _value
    
                    _smsg += _fmt_obj_chg_attr
    
                    _status = 0

        except self.ObjectOperationException, obj :
            _status = 8
            _xfmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 8
            _xfmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _xfmsg = str(e)

        finally :
            if _status :
                _msg = _fmsg + _xfmsg
                cberr(_fmsg)
            else :
                if obj_attr_list["specified_kv_pairs"].count("experiment_id") :
                    _msg = "The attribute \" experiment_id \" was changed."
                    _msg += " Checking if a Host OS performance data collection"
                    _msg += " daemon restart is needed."
                    cbdebug(_msg)
                    self.update_host_os_perfmon(obj_attr_list)
                _msg = _smsg
                cbdebug(_smsg)

            return self.package(_status, _msg, _result)

    @trace
    def show_view(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''        
        try :
            _fmsg = ""
            _status = 100
            _obj_type = "undefined"

            _criterion = "byundefined"
            _expression = "undefined"
            _filter = "undefined"
            _sorting = "arrival"
            _result = []

            obj_attr_list["cloud_name"] = "undefined"

            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

            if not _status :
                _obj_type =  obj_attr_list["object_type"]
                _criterion = "BY" + obj_attr_list["criterion"] 
                _expression = obj_attr_list["expression"]
                _sorting = obj_attr_list["sorting"]
                _filter = obj_attr_list["filter"]

                _fields = []
    
                _fields.append("|Object Type                 ")
                _fields.append("|Predicate                        ")

                _expression_list = self.osci.query_by_view(obj_attr_list["cloud_name"], _obj_type, _criterion, _expression, _sorting, _filter, True)
                _fields.append("|Object UUID                           ")
                _fields.append("|Object Name            ")
                _fields.append("|" + _sorting.capitalize() + " Time                       ")
                _fmt_obj_list = ''.join(_fields) + '\n'
                for _item in _expression_list :
                    if _expression_list.index(_item) == 0 :
                        _fmt_obj_list += ('|' + _obj_type).ljust(len(_fields[0]))
                        _fmt_obj_list += ("|where " + _criterion.upper() + " = " +  _expression).ljust(len(_fields[1]))
                    else :
                        _fmt_obj_list += ('|').ljust(len(_fields[0]))
                        _fmt_obj_list += ('|').ljust(len(_fields[1]))
                    _uuid, _name = _item[0].split('|')
                    _result.append({"uuid" : _uuid, "name" : _name})
                    _fmt_obj_list += ('|' + _uuid).ljust(len(_fields[2]))
                    _fmt_obj_list += ('|' + _name).ljust(len(_fields[3]))
                    if _item[1] != "Empty" :
                        _hrtf = asctime(localtime(float(_item[1])))
                    else :
                        _hrtf = "Empty"
                    _fmt_obj_list += ('|' + _hrtf + " (" + str(_item[1]) + ')').ljust(len(_fields[4]))
                    _fmt_obj_list += '\n'

                _status = 0

        except self.ObjectOperationException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if not _expression :
                _expression = _filter
            if _status :
                _msg = "Unable to get the list of " + _obj_type + " objects "
                _msg += "available on the view \"" + _criterion + "\" where \""
                _msg += _criterion + " = " + _expression + "\" on this "
                _msg += "experiment (Cloud "
                _msg += obj_attr_list["cloud_name"]  + "), sorted by "
                _msg += _sorting + "): " + _fmsg
                cberr(_msg)
            else :
                _msg = "The following " + _obj_type + " objects are part of the"
                _msg += " view \"" + _criterion + "\" where \""
                _msg += _criterion + " = " + _expression + "\" on this "
                _msg += "experiment (Cloud "
                _msg += obj_attr_list["cloud_name"]  + "), sorted by " 
                _msg += _sorting + ") :\n" + _fmt_obj_list
                cbdebug(_msg)
                
            return self.package(_status, _msg, _result)

    @trace
    def stats(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _result = []
            result_idx = 0
            
            obj_attr_list["cloud_name"] = "undefined"
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

                if not _status :
                    _query_object = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "query", False)
    
                    _fmt_obj_list = "------------------------- OBJECT STORE -----------------------\n"
                    _result.append(["Object Store", "Metric", "Value", []])
    
                    _info = self.osci.get_info()
                    _fields = []
    
                    _fields.append("|Metric                                               ")
                    _fields.append("|Value                         ")
                    _fmt_obj_list += ''.join(_fields) + '\n'
                    for _line in _info :
                        _result[result_idx][3].append((_line[0], str(_line[1])))
                        _fmt_obj_list += ('|' + _line[0]).ljust(len(_fields[0]))
                        _fmt_obj_list += ('|' + _line[1]).ljust(len(_fields[1]))
                        _fmt_obj_list += '\n'
    
                    _fmt_obj_list += "------------------------- METRIC STORE -----------------------\n"
                    result_idx += 1
                    _result.append(["Metric Store", "Metric", "Value", []])
    
                    _info = self.msci.get_info()
                    _fields = []
    
                    _fields.append("|Metric                                               ")
                    _fields.append("|Value                         ")
                    _fmt_obj_list += ''.join(_fields) + '\n'
                    for _line in _info :
                        _result[result_idx][3].append((_line[0], str(_line[1])))
                        _fmt_obj_list += ('|' + _line[0]).ljust(len(_fields[0]))
                        _fmt_obj_list += ('|' + _line[1]).ljust(len(_fields[1]))
                        _fmt_obj_list += '\n'
    
                    _fmt_obj_list += "--------------------- EXPERIMENT OBJECTS ---------------------\n" 
                    result_idx += 1
                    _result.append(["Experiment Objects", "Object", "Count", []])
                    _fields = []
    
                    _fields.append("|Object                                               ")
                    _fields.append("|Count                         ")
                    _fmt_obj_list += ''.join(_fields) + '\n'
    
                    for _obj_type in _query_object["object_type_list"].split(',') :
                        _obj_count = self.get_object_count(obj_attr_list["cloud_name"], _obj_type)
                        _result[result_idx][3].append((_obj_type + 's', str(_obj_count)))
                        _fmt_obj_list += ('|' + _obj_type + 's').ljust(len(_fields[0]))
                        _fmt_obj_list += ('|' + _obj_count ).ljust(len(_fields[1]))
                        _fmt_obj_list += '\n'
                    
                    _fmt_obj_list += "------------------ EXPERIMENT-WIDE COUNTERS ------------------\n" 
                    result_idx += 1
                    _result.append(["Experiment-Wide Counters", "Counter", "Value", []])
                    _fields = []
    
                    _fields.append("|Counter                                              ")
                    _fields.append("|Value                         ")
                    _fmt_obj_list += ''.join(_fields) + '\n'
    
                    for _obj_type in _query_object["object_type_list"].split(',') :
                        _result[result_idx][3].append((_obj_type + ' Reservations', str(self.get_object_count(obj_attr_list["cloud_name"], _obj_type, "RESERVATIONS"))))
                        _fmt_obj_list += ('|' + _obj_type + " RESERVATIONS").ljust(len(_fields[0]))
                        _fmt_obj_list += ('|' + _result[result_idx][3][-1][1]).ljust(len(_fields[1]))
                        _fmt_obj_list += '\n'
                        _result[result_idx][3].append((_obj_type + 's Arrived', str(self.get_object_count(obj_attr_list["cloud_name"], _obj_type, "ARRIVED"))))
                        _fmt_obj_list += ('|' + _obj_type + "s ARRIVED").ljust(len(_fields[0]))
                        _fmt_obj_list += ('|' + _result[result_idx][3][-1][1]).ljust(len(_fields[1]))
                        _fmt_obj_list += '\n'
                        _result[result_idx][3].append((_obj_type + 's Arriving', str(self.get_object_count(obj_attr_list["cloud_name"], _obj_type, "ARRIVING"))))
                        _fmt_obj_list += ('|' + _obj_type + "s ARRIVING").ljust(len(_fields[0]))
                        _fmt_obj_list += ('|' + _result[result_idx][3][-1][1]).ljust(len(_fields[1]))
                        _fmt_obj_list += '\n'
                        if _obj_type == "VM" or _obj_type == "AI" :
                            _result[result_idx][3].append((_obj_type + 's Capturing', str(self.get_object_count(obj_attr_list["cloud_name"], _obj_type, "CAPTURING"))))
                            _fmt_obj_list += ('|' + _obj_type + "s CAPTURING").ljust(len(_fields[0]))
                            _fmt_obj_list += ('|' + _result[result_idx][3][-1][1]).ljust(len(_fields[1]))
                            _fmt_obj_list += '\n'
                        _result[result_idx][3].append((_obj_type + 's Departed', str(self.get_object_count(obj_attr_list["cloud_name"], _obj_type, "DEPARTED"))))
                        _fmt_obj_list += ('|' + _obj_type + "s DEPARTED").ljust(len(_fields[0]))
                        _fmt_obj_list += ('|' + _result[result_idx][3][-1][1]).ljust(len(_fields[1]))
                        _fmt_obj_list += '\n'
                        _result[result_idx][3].append((_obj_type + 's Departing', str(self.get_object_count(obj_attr_list["cloud_name"], _obj_type, "DEPARTING"))))
                        _fmt_obj_list += ('|' + _obj_type + "s DEPARTING").ljust(len(_fields[0]))
                        _fmt_obj_list += ('|' + _result[result_idx][3][-1][1]).ljust(len(_fields[1]))
                        _fmt_obj_list += '\n'
                        _result[result_idx][3].append((_obj_type + 's Failed', str(self.get_object_count(obj_attr_list["cloud_name"], _obj_type, "FAILED"))))
                        _fmt_obj_list += ('|' + _obj_type + "s FAILED").ljust(len(_fields[0]))
                        _fmt_obj_list += ('|' + _result[result_idx][3][-1][1]).ljust(len(_fields[1]))
                        _fmt_obj_list += '\n'
    
                    _result[result_idx][3].append(("Experiment Counter", str(self.osci.count_object(obj_attr_list["cloud_name"], "GLOBAL", "experiment_counter"))))
                    _fmt_obj_list += "|EXPERIMENT COUNTER".ljust(len(_fields[0]))
                    _fmt_obj_list += ('|' + _result[result_idx][3][-1][1]).ljust(len(_fields[1]))
                    _fmt_obj_list += '\n'
    
                    _vmc_uuid_list = self.osci.get_object_list(obj_attr_list["cloud_name"], "VMC")
                    if _vmc_uuid_list :
                        result_idx += 1
                        _result.append(["VMC-Wide Counters", "Hypervisor / Region", "Virtual Machines", []])
                        _fmt_obj_list += "\n ---------------- VMC-WIDE COUNTERS ----------------\n"
                        for _vmc_uuid in _vmc_uuid_list :
                            _vmc_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "VMC", False, _vmc_uuid, False)
                            _result[result_idx][3].append((_vmc_attr_list["name"] + " VM Reservations", str(_vmc_attr_list["nr_vms"])))
                            _fmt_obj_list += ('|' + _vmc_uuid + " (" + _vmc_attr_list["name"] + ") VM RESERVATIONS").ljust(len(_fields[0]))
                            _fmt_obj_list += ('|' + _result[result_idx][3][-1][1]).ljust(len(_fields[1]))
                            _fmt_obj_list += '\n'
    
                    _aidrs_uuid_list = self.osci.get_object_list(obj_attr_list["cloud_name"], "AIDRS")
                    if _aidrs_uuid_list :
                        result_idx += 1
                        _result.append(["AIDRS-Wide Counters", "Submitter", "Virtual Applications", []])
                        _fmt_obj_list += "\n ---------------- AIDRS-WIDE COUNTERS ----------------\n"
                        for _aidrs_uuid in _aidrs_uuid_list :
                            _aidrs_attr_list = self.osci.get_object(obj_attr_list["cloud_name"], "AIDRS", False, _aidrs_uuid, False)
                            _result[result_idx][3].append((_aidrs_attr_list["name"] + " AI Reservations", str(_aidrs_attr_list["nr_ais"])))
                            _fmt_obj_list += ('|' + _aidrs_uuid + " (" + _aidrs_attr_list["name"] + ") AI RESERVATIONS").ljust(len(_fields[0]))
                            _fmt_obj_list += ('|' + _result[result_idx][3][-1][1]).ljust(len(_fields[1]))
                            _fmt_obj_list += '\n'

                    _status = 0

        except self.ObjectOperationException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Unable to get the values of the counters available on "
                _msg += "this experiment (Cloud "
                _msg += obj_attr_list["cloud_name"] + "): " + _fmsg
                cberr(_msg)
            else :
                _msg = "The following statistics are available on this "
                _msg += "experiment (Cloud " + obj_attr_list["cloud_name"]
                _msg += ") :\n" + _fmt_obj_list
                cbdebug(_msg)
            return self.package(_status, _msg, _result)

    @trace
    def show_state(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _obj_type = "undefined"
            _result = []

            obj_attr_list["cloud_name"] = "undefined"
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if "filter" in obj_attr_list :
                _filter = obj_attr_list["filter"]
                del obj_attr_list["filter"]
            else :
                _filter = False
                
            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

                
            if not _status :
                _fmt_obj_header = "------------------ PER-OBJECT STATE (CLOUD "
                _fmt_obj_header += obj_attr_list["cloud_name"] + ")  -----------------\n" 
                _fields = []
                _fmt_obj_list = ""

                _fields.append("|Object Type    ")
                _fields.append("|Object Name    ")
                _fields.append("|Object UUID                             ")
                _fields.append("|State                     ")
                _fmt_obj_list += ''.join(_fields) + '\n'
                _query_object = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "query", False)

                _count = 0
                
                for _obj_type in _query_object["object_type_list"].split(',') :
                    _obj_list = self.osci.get_object_list(obj_attr_list["cloud_name"], _obj_type)
                    if _obj_list :
                        for _obj_uuid in _obj_list :
                            _obj_state = self.osci.get_object_state(obj_attr_list["cloud_name"], _obj_type, _obj_uuid)
                            _obj_name = self.get_object_attribute(obj_attr_list["cloud_name"], \
                                                    _obj_type, _obj_uuid, "name")
                            if _filter and _obj_state != _filter :
                                continue
                            
                            _result.append({"type" : _obj_type, "name" : _obj_name, "uuid" : _obj_uuid, "state" : _obj_state})
                            
                            _fmt_obj_list += ('|' + _obj_type).ljust(len(_fields[0]))
                            _fmt_obj_list += ('|' + _obj_name).ljust(len(_fields[1]))
                            _fmt_obj_list += ('|' + _obj_uuid).ljust(len(_fields[2]))
                            _fmt_obj_list += ('|' + _obj_state).ljust(len(_fields[3]))
                            _fmt_obj_list += '\n'
                            _count += 1
                            
                if _count > 0 :
                    _fmt_obj_list = _fmt_obj_header + _fmt_obj_list
                else :
                    _fmt_obj_list = "No objects available.\n"

                _status = 0

        except self.ObjectOperationException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Unable to get the values of the state for objects on "
                _msg += "this experiment (Cloud "
                _msg += obj_attr_list["cloud_name"] + "): " + _fmsg
                cberr(_msg)
            else :
                _msg = "The following state values are available for the objects"
                _msg +=" on this experiment (Cloud "
                _msg += obj_attr_list["cloud_name"] + ") :\n" + _fmt_obj_list
                cbdebug(_msg)
                
            return self.package(_status, _msg, _result)

    @trace
    def alter_state(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            
            obj_attr_list["name"] = "undefined"
            obj_attr_list["cloud_name"] = "undefined"
            _old_state = "undefined"
            _result = None
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

            if not _status :
                _query_object = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, "query", False)

                for _obj_type in _query_object["object_type_list"].split(',') :
                    _obj_uuid = self.osci.object_exists(obj_attr_list["cloud_name"], _obj_type, obj_attr_list["name"], True)
                    if _obj_uuid :
                        _old_state = str(self.osci.get_object_state(obj_attr_list["cloud_name"], _obj_type, _obj_uuid))
                        str(self.osci.set_object_state(obj_attr_list["cloud_name"], _obj_type, _obj_uuid, obj_attr_list["specified_state"]))
                        break
                _result = obj_attr_list
                _status = 0

        except self.ObjectOperationException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Unable to get the state value for the object \""
                _msg += obj_attr_list["name"] + "\" on this "
                _msg += "this experiment (Cloud "
                _msg += obj_attr_list["cloud_name"] + "): " + _fmsg
                cberr(_msg)
            else :
                _msg = "The " + _obj_type.upper() + " object " + obj_attr_list["name"]
                _msg += " had its state altered from \"" + _old_state + "\" to "
                _msg += "\"" + obj_attr_list["specified_state"] + "\""
                _msg +=" on this experiment (Cloud "
                _msg += obj_attr_list["cloud_name"] + ")\n"
                cbdebug(_msg)
            return self.package(_status, _msg, _result)

    @trace
    def wait_for(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _obj_type = command.split('-')[0].upper()

            obj_attr_list["cloud_name"] = "undefined"
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _vg = ValueGeneration(self.pid)
                _time_to_wait = int(_vg.time2seconds(obj_attr_list["specified_time"]))   
                
                if obj_attr_list["interval"] == "default" or obj_attr_list["interval"] == "0" :
                    if _time_to_wait > 10 :
                        _update_interval = 10
                    else :
                        _update_interval = max(1,_time_to_wait/10)
                else :
                    _update_interval = _time_to_wait/int(obj_attr_list["interval"])

                _msg = "Going to unconditionally wait for "
                _msg += obj_attr_list["specified_time"] + " (" + str(_time_to_wait)
                _msg += " seconds). The command line interface will be blocked"
                _msg += " during the waiting."
                print _msg
                
                _start_time = int(time())
                _elapsed_time = 0
                while _elapsed_time < _time_to_wait :
                    _remaining_time = _time_to_wait - (int(time()) - _start_time)
                    if _remaining_time < _update_interval :
                        _update_interval = _remaining_time 
                    sleep(_update_interval)
                    _elapsed_time = int(time()) - _start_time
                    _msg = "Waited " + str(_elapsed_time) + " seconds... (" 
                    _msg += str(float(_elapsed_time)*100/float(_time_to_wait)) + "%)" 
                    print _msg

                _status = 0

        except ValueGeneration.ValueGenerationException, obj :
            _status = 28
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Error while \"waiting for\": " + _fmsg
                cberr(_msg)
            else :
                _msg = "Waited for " + str(_time_to_wait) + " seconds."
                cbdebug(_msg)
            return self.package(_status, _msg, None)
        
    @trace
    def wait_until(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _obj_type = "undefined"

            obj_attr_list["cloud_name"] = "undefined"

            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)
            
            if not _status :
                
                _obj_type = obj_attr_list["type"].upper()

                if len(obj_attr_list["counter"]) :
                    _counter_type = obj_attr_list["counter"]
                    _counter_name = obj_attr_list["counter"]
                else :
                    _counter_type = False
                    _counter_name = "(Objects created on the Object Store)"
                
                if obj_attr_list["direction"] == "increasing" :
                    _direction = "increasing"
                elif obj_attr_list["direction"] == "decreasing" :
                    _direction = "decreasing"
                else :
                    _msg = "Unknown direction for counter: " + str(obj_attr_list["direction"])
                    _status = 716
                    cberr(_msg)
                    raise self.ObjectOperationException(_msg, _status)            

                _counter_value = self.get_object_count(obj_attr_list["cloud_name"], _obj_type, _counter_type)                
                if _counter_value != "-1" :
                    True
                else :
                    _msg = "Warning: The specified counter (" + _counter_name + ')'
                    _msg += " does not exist. Will keep polling and checking anyway."
                    cbdebug(_msg)

                _check_interval = float(obj_attr_list["interval"])
                _start_time = int(time())

                if _counter_value :
                    _msg = "Going to wait until the value on counter \"" + _obj_type
                    _msg += ' ' + _counter_name + "\" is equal to " + str(obj_attr_list["value"])
                    _msg += " (currently it is equal to " + str(_counter_value) + ") "
                    _msg += "waiting " + str(_check_interval) + " seconds between "
                    _msg += "samples. The counter is assumed to be " + _direction + '.'
                    print _msg
                
                    while True :
                        sleep(_check_interval)
                        _current_time = int(time())

                        _counter_value = self.get_object_count(obj_attr_list["cloud_name"], _obj_type, _counter_type)

                        _msg = "Counter \"" + _obj_type + ' ' + _counter_name
                        _msg += "\" equals " + str(_counter_value) + " after "
                        _msg += str(_current_time - _start_time) + " seconds ("
                        _msg += "the counter is assumed to be " + _direction + ")."
                        cbdebug(_msg, True)

                        if _direction == "increasing" and int(_counter_value) >= int(obj_attr_list["value"]) :
                            break
                        elif _direction == "decreasing" and int(_counter_value) <= int(obj_attr_list["value"]) :
                            break

                    _status = 0

                else:
                    _fmsg = "Counter \"" + _obj_type + ' ' + _counter_name + "\""
                    _fmsg += " does not exist."
                    _status = 34

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except self.ObjectOperationException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Error while \"waiting until\": " + _fmsg
                cberr(_msg)
            else :
                _current_time = int(time())
                _msg = "Waited " + str(_current_time - _start_time) + " seconds"
                _msg += " until \"" + _obj_type + "s " + _counter_name
                _msg += "\" was equal to " + str(obj_attr_list["value"]) + '.'
                cbdebug(_msg)
            return _status, _msg, None

    @trace
    def wait_on(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _obj_type = "undefined"

            obj_attr_list["cloud_name"] = "undefined"
            obj_attr_list["channel"] = "undefined"

            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)
            
            if not _status :

                _obj_type = obj_attr_list["type"].upper()                
                _sub_channel = self.osci.subscribe(obj_attr_list["cloud_name"], _obj_type, obj_attr_list["channel"])

                _msg = "Subscribed to channel \"" + obj_attr_list["channel"] + "\""
                _msg += " (object \"" + _obj_type + "\" listening for messages with"
                _msg += " the keyword \"" + obj_attr_list["keyword"] + "\")"
                print _msg

                for _message in _sub_channel.listen() :
                    if _message["type"] == "message" :
                        _msg = "Message received (" + _message["data"] 
                        _msg += "). Proceeding to parse it"
                        cbdebug(_msg)

                        if _message["data"].count(obj_attr_list["keyword"]) :
                            _msg = "Message \"" + _message["data"] + "\" received"
                            _msg += " on channel \"" + obj_attr_list["channel"]
                            _msg += "\"."
                            cbdebug(_msg)
                            _sub_channel.unsubscribe()
                            break

                _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Error while \"waiting on channel\": " + _fmsg
                cberr(_msg)
            else :
                _msg = "Waited until a message containing the keyword \"" + obj_attr_list["keyword"]
                _msg += "\" was received on the channel \"" + obj_attr_list["channel"]
                _msg += "\" ( " + _obj_type + ")."
                cbdebug(_msg)

            return _status, _msg, None

    @trace
    def msgpub(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _obj_type = "undefined"

            obj_attr_list["cloud_name"] = "undefined"
            obj_attr_list["channel"] = "undefined"

            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)
            
            if not _status :

                _obj_type = obj_attr_list["type"].upper()                
                self.osci.publish_message(obj_attr_list["cloud_name"], _obj_type, obj_attr_list["channel"], obj_attr_list["message"], 1, 3600)

                _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = obj.status
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Error while publishing message: " + _fmsg
                cberr(_msg)
            else :
                _msg = "Message \"" + obj_attr_list["message"] + "\""
                _msg += " published on channel \"" + obj_attr_list["channel"] 
                _msg += "\" (object \"" + _obj_type + "\" )."
                cbdebug(_msg)

            return _status, _msg, None

    @trace
    def debug_startup(self, obj_attr_list, params, cmd) :
        '''
        TBD
        '''
        try :
            _status = 100
            
            _fmsg = "An error has occurred, but no error message was captured"
            _status, _fmsg = self.parse_cli(obj_attr_list, params, cmd)
            _smsg = ""
    
            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, cmd)
    
            if not _status :
                if "qemu_debug" in obj_attr_list and obj_attr_list["qemu_debug"].lower() == "true" :
                    port = obj_attr_list["qemu_debug_port"]
                elif "svm_qemu_debug" in obj_attr_list and obj_attr_list["svm_qemu_debug"].lower() == "true" :
                    port = obj_attr_list["svm_qemu_debug_port"]
                else :
                    return (443, "Debugging not enabled for this object.", None)
                
                _cmd = "xterm -fg white -bg black -e gdb "
                _cmd += obj_attr_list["qemu_binary"] + " "
                _cmd += " -ex \"target remote " + obj_attr_list["vmc_name"] + ":" + port + "\""
                _cmd += " -ex \"handle SIGUSR2 noprint\""
                for breakpoint in obj_attr_list["breakpoints"] :
                    _cmd += " -ex \"b " + breakpoint + "\""
                _cmd += " -ex \"continue\""
                _proc_h = Popen(_cmd, shell=True, stdout=PIPE, stderr=PIPE)
        
                if _proc_h.pid :
                    _xmsg = "Console command \"" + _cmd + "\" "
                    _xmsg += " was successfully started. "
                    _smsg = _xmsg + " The process id is " + str(_proc_h.pid) + "."
                    
                    if not cmd.count("svm") :
                        _cld_ops_class = self.get_cloud_class(obj_attr_list["model"])
                        _cld_conn = _cld_ops_class(self.pid, self.osci)
                        sleep(2)
                        unused, unused2 = _cld_conn.vm_fixpause(obj_attr_list)
                    _status = 0
                        
        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 40
            _fmsg = str(obj.msg)
            
        finally :
            if _status :
                _msg ="Debug attachment failure: " + _fmsg 
                cberr(_msg)
            else :
                _msg = "Debug attachment success (" + _smsg + ")."
                cbdebug(_msg)

        return 0, _msg, None

    @trace
    def monitoring_extractall(self, parameters, command) :
        '''
        TBD
        '''
        try : 
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _smsg = ''
            if BaseObjectOperations.default_cloud is not None:
                _cn = BaseObjectOperations.default_cloud
            else :
                if len(parameters.split()) > 1 :
                    _cn = parameters.split()[0]
                else :
                    _status = 9
                    _msg = "Usage: monextract <cloud name> all"
                    raise self.ObjectOperationException(_msg, 11)

            _cloud_list = self.osci.get_object_list("ITSELF", "CLOUD")

            if _cloud_list and _cn in list(_cloud_list) :
                # Cloud is attached, we can proceed
                True
            else :
                _msg = "The cloud \"" + _cn + "\" is not yet attached "
                _msg += "to this experiment. Please attach it first."
                _status = 9876
                raise self.ObjectOperationException(_msg, _status)
            
            self.monitoring_extract(_cn + " HOST os", "mon-extract")
            self.monitoring_extract(_cn + " VM os", "mon-extract")
            self.monitoring_extract(_cn + " VM app", "mon-extract")
            self.monitoring_extract(_cn + " VM management", "mon-extract")

            _status = 0
            
        except self.ObjectOperationException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except self.msci.MetricStoreMgdConnException, obj :
            _status = 40
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status and _status != 1111:
                _msg = "Monitor extraction failure: " + _fmsg
                cberr(_msg)
            else :
                _msg = "Monitor extraction success. All metrics written to csv"
                _msg += " files on the current directory."
                cbdebug(_msg)
            return _status, _msg
        
    @trace
    def monitoring_extract(self, parameters, command) :
        '''
        TBD
        '''
        try : 
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _obj_attr_list = {}
            _status, _fmsg = self.parse_cli(_obj_attr_list, parameters, command)
            _msg = ""

            if not _status :
                _status, _fmsg = self.initialize_object(_obj_attr_list, command)

                if not _status :
                    _obj_type = _obj_attr_list["type"].lower()
    
                    _metric_type = _obj_attr_list["metric_type"].lower()
                    
                    if _metric_type == "m" or _metric_type == "mgt" or _metric_type == "man" or _metric_type == "management" :
                        _metric_type = "management"
                    elif _metric_type == "a" or _metric_type == "app" or _metric_type == "application" and _obj_type == "VM" :
                        _metric_type = "runtime_app"
                    elif _metric_type == "os" or _metric_type == "system" or _metric_type == "operatingsystem" :
                        _metric_type = "runtime_os"
                    else :
                        _msg = "Metrics of type \"" + _metric_type + "\" are not available for \"" + _obj_type + "\" objects." 
                        _status = 1028
                        raise self.ObjectOperationException(_msg, _status)
                        
                    if _obj_attr_list["expid"] == "current" :
                        _criteria = { "expid" : _obj_attr_list["current_experiment_id"] }
                    else :
                        _criteria = { "expid" : _obj_attr_list["expid"] }
                    
                    _csv_contents_header = _obj_attr_list[_obj_type + '_' + _metric_type + "_metrics_header"]
    
                    _fn = _obj_attr_list["data_file_location"] + '/' 
                    _fn += _obj_type.upper() + '_' + _metric_type + '_'
                    _fn += _criteria["expid"] + ".csv"
                    _fd = open(_fn, 'w', 0)
    
                    _fd.write("#field:column #\n")
                    for _index, _item in enumerate(_csv_contents_header.split(',')) :
                        _fd.write('#' + _item + ':' + str(_index + 1) + '\n')
                    _fd.write("\n")
    
                    _msg = "Preparing to extract " + _metric_type + " metrics for all "
                    _msg += _obj_type.upper() + " objects with experiment id \"" 
                    _msg += str(_obj_attr_list["expid"]) + "\""
                    cbdebug(_msg)
    
                    _fd.write(_csv_contents_header + '\n')
                    
                    _msg = "Populating in-memory cache with an \"UUID to attribute\""
                    _msg += " cache for all " + _obj_type.upper() + " objects."
                    cbdebug(_msg)
                
                    _uuid_to_attr_dict = {}
                    
                    _desired_keys = _csv_contents_header.split(',')
                    
                    # Management metrics collection is always extracted, because it 
                    # contains all the information that maps UUIDs to all other attributes.
                    # Given that a user can change the "experiment id" after a given
                    # object was attached, we get all management metrics for the 
                    # UUID to other attribute map, but only print the metrics pertaining
                    # to the current "experiment id". This needs to be optimized 
                    # later.
                    _management_metrics_list = self.msci.find_document("management_" + _obj_type.upper() + '_' + _obj_attr_list["username"], {}, True)
                    
                    for _metric in _management_metrics_list :
                        _csv_contents_line = ''
                        for _key in _desired_keys  :
                            if _metric["expid"] == _criteria["expid"] :
                                if _key in _metric :
                                    _csv_contents_line += str(_metric[_key]) + ','
                                else :
                                    _csv_contents_line += _obj_attr_list["filler_string"] + ','
    
                            # The uuid to attribute cache/map has to be unconditionally
                            # populated.
                            _uuid_to_attr_dict[_metric["_id"]] = _metric
        
                        if _metric_type == "management" :
                            _csv_contents_line = _csv_contents_line[:-1] + '\n'
                            _fd.write(_csv_contents_line)
    
                    _msg = "Done populating cache"
                    cbdebug(_msg)
    
                    if _metric_type == "management" :
        
                        _trace_csv_contents_header = _obj_attr_list["trace_header"]
        
                        _trace_desired_keys = _trace_csv_contents_header.split(',')
    
                        _trace_fn = _obj_attr_list["data_file_location"] + '/' 
                        _trace_fn += "trace_" 
                        _trace_fn += _criteria["expid"] + ".csv"
                        _trace_fd = open(_trace_fn, 'w', 0)
    
                        _trace_fd.write("#field:column #\n")
                        for _index, _item in enumerate(_trace_csv_contents_header.split(',')) :
                            _trace_fd.write('#' + _item + ':' + str(_index) + '\n')
                        _trace_fd.write("\n")
    
                        _trace_fd.write(_trace_csv_contents_header + '\n')
                        
                        _trace_list = self.msci.find_document("trace_" + _obj_attr_list["username"], _criteria, True)
    
                        for _trace_item in _trace_list :
                            _trace_csv_contents_header = ''
                            for _key in _trace_desired_keys  :
                                if _key in _trace_item :
                                    _trace_csv_contents_header += str(_trace_item[_key]) + ','
                                else :
                                    _trace_csv_contents_header += _obj_attr_list["filler_string"] + ','
    
                            _trace_csv_contents_header = _trace_csv_contents_header[:-1] + '\n'
                            _trace_fd.write(_trace_csv_contents_header)
    
                        _trace_fd.close()
                    
                    if _metric_type == "runtime_os" or _metric_type == "runtime_app" :
                        _last_unchanged_metric = {}
    
                        _runtime_metric_list = self.msci.find_document(_metric_type + '_' + _obj_type.upper() + '_' + _obj_attr_list["username"], _criteria, True)
    
                        for _metric in _runtime_metric_list :
                            
                            _current_uuid = _metric["uuid"]
                            _csv_contents_line = ''
    
                            if not _current_uuid in _last_unchanged_metric :
                                # This is another dictionary, used to 
                                # "carry over" runtime metrics that are not reported
                                # frequently, because they change infrequently. For
                                # instance "cpu_freq" is reported with a very low
                                # frequency. To save memory and storage, the gmetad
                                # DOES NOT write "old" values to the Metric Store.
                                # However, we do need these values for the building
                                # of the csv, and thus we just "borrow" the previous
                                # value when a metric is not found on the Metric Store.
                                _last_unchanged_metric[_current_uuid] = {}
    
                            for _key in _desired_keys :
                                if _key in _metric and _key != "uuid" and _key != "time" and _key != "time_h" :
                                    _val = str(_metric[_key]["val"])
                                    # Every time we find a metric, we add it to an
                                    # in-memory cache (dictionary)
                                    _last_unchanged_metric[_current_uuid][_key] = str(_val)
    
                                elif _key == "uuid" or _key == "time_h" :
                                    _val = str(_metric[_key])
    
                                elif _key == "time" :
                                    _val = str(int(_metric[_key]))
    
                                elif _metric["uuid"] in _uuid_to_attr_dict and _key in _uuid_to_attr_dict[_metric["uuid"]] :
                                    _val = str(_uuid_to_attr_dict[_metric["uuid"]][_key])
    
                                else :
                                    if _key in _last_unchanged_metric[_current_uuid] :
                                        # Every time a metric is not found, we just
                                        # replay it from the in-memory cache (dictionary)
                                        _val = str(_last_unchanged_metric[_current_uuid][_key]) + " (unchanged)"
                                    else :
                                        _val = _obj_attr_list["filler_string"]
                                _csv_contents_line += _val + ','
                                
                            _fd.write(_csv_contents_line[:-1] + '\n')
    
                    _fd.close()
                            
                    _msg = _metric_type + " metrics for all " + _obj_type.upper()
                    _msg += " objects were successfully extracted. File name is "
                    _msg += _fn + ' .'
                    cbdebug(_msg)
    
                    _status = 0

        except self.ObjectOperationException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except self.msci.MetricStoreMgdConnException, obj :
            _status = 40
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status and _status != 1111:
                _msg = "Monitor extraction failure: " + _fmsg
                cberr(_msg)
            else :
                _msg = "Monitor extraction success. " + _obj_type.upper()
                _msg += ' ' + _metric_type.replace("_app", " application").replace("_os", " OS")
                _msg += " performance data samples were written to the file " + _fn + '.'
                cbdebug(_msg)
            return _status, _msg

    @trace
    def monitoring_list(self, parameters, command) :
        '''
        TBD
        '''
        try : 
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _result = {"management" : [], "runtime" : []} 
            _obj_attr_list = {}
            _status, _fmsg = self.parse_cli(_obj_attr_list, parameters, command)
            _msg = ""

            if not _status :
                _status, _fmsg = self.initialize_object(_obj_attr_list, command)

                if not _status :
                    _curr_time = int(time())
                    _obj_type = _obj_attr_list["type"]
                    
                    _msg = "The following " + _obj_type + "s reported management metrics:\n"
                    _field1 = "Name                        "
                    _field2 = "Age (seconds)"
                    _msg += _field1 + '|' + _field2 + '\n'

                    _metrics_list = self.msci.find_document("latest_management_" + _obj_type + '_' + _obj_attr_list["username"], {}, True)
                    
                    for _metric in _metrics_list :
                        _msg += _metric["name"].ljust(len(_field1))
                        _msg += '|' + str( _curr_time- int(_metric["mgt_001_provisioning_request_originated"])).ljust(len(_field2)) + '\n'

                    _msg += "\nThe following " + _obj_type  + "s reported runtime (OS) metrics:\n"
                    _msg += _field1 + '|' + _field2 + '\n'

                    _metrics_list = self.msci.find_document("latest_runtime_os_" + _obj_type + '_' + _obj_attr_list["username"], {}, True)
                    
                    for _metric in _metrics_list :
                        _obj_attr_list = self.osci.get_object(_obj_attr_list["cloud_name"], _obj_type, False, _metric["_id"], False)
                        _result["runtime"].append([_obj_attr_list["name"], _obj_attr_list["time"]])
                        _msg += _obj_attr_list["name"].ljust(len(_field1))
                        _msg += '|' +  str( _curr_time- int(_metric["time"])).ljust(len(_field2)) + '\n'

                    if _obj_type == "VM" :
                        _msg += "\nThe following " + _obj_type  + "s reported runtime (Application) metrics:\n"
                        _msg += _field1 + '|' + _field2 + '\n'
                        
                        _metrics_list = self.msci.find_document("latest_runtime_app_" + _obj_type + '_' + _obj_attr_list["username"], {}, True)

                        for _metric in _metrics_list :
                            _result["management"].append([_obj_attr_list["name"], _obj_attr_list["time"]])
                            _obj_attr_list = self.osci.get_object(_obj_attr_list["cloud_name"], _obj_type, False, _metric["_id"], False)
                            _msg += _obj_attr_list["name"].ljust(len(_field1))
                            _msg += '|' +  str( _curr_time- int(_metric["time"])).ljust(len(_field2)) + '\n'                                               

                    _status = 0

        except self.ObjectOperationException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except self.msci.MetricStoreMgdConnException, obj :
            _status = 40
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status and _status != 1111:
                _msg = "Monitor extraction failure: " + _fmsg
                cberr(_msg)
            else :
                cbdebug(_msg)
            return self.package(_status, _msg, _result)
            
    @trace
    def run_api_service(self, passive, active, background, debug, port, hostname) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            self.wait_for_port_ready(hostname, port)
            from lib.api.api_service import APIService
            apiservice = APIService(self.pid, \
                                    passive, \
                                    active, \
                                    background, \
                                    debug, \
                                    port, \
                                    hostname)
            if debug :
                apiservice.run()
            else :
                apiservice.start()
            while True :
                sleep(10)
            apiservice.stop()
            apiservice.join()
            _status = 0

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "API Service startup failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "API Service startup success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def cloud_watch(self, cloud_name, uuid) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _cloud_parameters = self.get_cloud_parameters(cloud_name)

            _cld_ops_class = self.get_cloud_class(_cloud_parameters["model"])
                
            _cld_conn = _cld_ops_class(self.pid, self.osci)

            for _vmc_uuid in self.osci.get_object_list(cloud_name, "VMC") : 
                _obj_attr_list = self.osci.get_object(cloud_name, "VMC", False, _vmc_uuid, False)
                _obj_attr_list["vmc_name"] = _obj_attr_list["name"]
                _vm_list = _cld_conn.get_vm_instances(_obj_attr_list) 
                if _vm_list :
                    for _vm in _vm_list :
                        print _vm.name, _vm.id, _vm.status
                        sleep(float(_obj_attr_list["update_frequency"]))
            _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 40
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Cloud Watch Service startup failure: " + _fmsg
                cberr(_msg)
                raise self.ObjectOperationException(_msg, _status)
            else :
                _msg = "Cloud Watch Service startup success."
                cbdebug(_msg)
                return _status, _msg

    @trace
    def execute_shell(self, parameters, command) :
        '''
        TBD
        '''
        try : 
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _obj_attr_list = {}
            _status, _fmsg = self.parse_cli(_obj_attr_list, parameters, command)
            _msg = ""

            if not _status :

                _status, _fmsg = self.initialize_object(_obj_attr_list, command)

                if not _status :
                    _cmd = _obj_attr_list["cmdexec"]

                    _proc_man =  ProcessManagement()
                    print "running shell command: \"" + _cmd + "\"...."
                    _status, _result_stdout, _result_stderr = _proc_man.run_os_command(_cmd)

                    if not _status :
                        print "stdout:\n " + _result_stdout

                        if len(_result_stderr) :
                            print "stderr:\n " + _result_stderr
                    else :
                        _fmsg = _result_stderr

        except self.ObjectOperationException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except self.msci.MetricStoreMgdConnException, obj :
            _status = 40
            _fmsg = str(obj.msg)

        except ProcessManagement.ProcessManagementException, obj :
            _status = str(obj.status)
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Shell command execution failure: " + _fmsg
                cberr(_msg)
            else :
                cbdebug(_msg)

            return _status, _msg, ''

    @trace
    def globallist(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _result = []

            _msg_string = {}
            _msg_string["vm_roles"] = " can be attached to "
            _msg_string["ai_types"] = " can be attached to "
            _msg_string["aidrs_patterns"] = " can be attached to "
            _msg_string["vmc_pools"] = " are attached to "
            _msg_string["view_criteria"] = " can be used on"
            
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

                if not _status :
                    _list_name = obj_attr_list["object_type"][:-1].lower() + '_' + obj_attr_list["object_attribute"]
        
                    _result = list(self.osci.get_list(obj_attr_list["cloud_name"], "GLOBAL", _list_name))
        
                    _list = ", ".join(_result)

                    _vmc_list = self.osci.get_object_list(obj_attr_list["cloud_name"], "VMC")

                    if not _vmc_list :
                        _vmc_list = []

                    if _list_name == "view_criteria" :
                        _view_dict = {
                                      "vmc" : { 
                                               "pool": [ 0, { "label" : "VMC Pool", "criterion" : "pool", "expression" : sorted(list(self.osci.get_list(obj_attr_list["cloud_name"], "GLOBAL", "vmc_pools"))) } ],
                                               "arrival": [ 1, { "label" : "Arrival Time", "criterion" : "username", "expression" : self.username } ],
                                               },

                                      "host" : { 
                                               "vmc": [ 0, { "label" : "VMC", "criterion" : "vmc", "expression" : sorted(list(_vmc_list)) } ],
                                               "arrival": [ 1, { "label" : "Arrival Time", "criterion" : "username", "expression" : self.username} ],
                                               },
                                      
                                      "vm" : { 
                                              "role": [ 0, { "label" : "Role", "criterion" : "role", "expression" : sorted(list(self.osci.get_list(obj_attr_list["cloud_name"], "GLOBAL", "vm_roles")))} ],
                                              "type": [ 1, { "label" : "Type", "criterion" : "type", "expression" : sorted(list(self.osci.get_list(obj_attr_list["cloud_name"], "GLOBAL", "ai_types")))} ],
                                              "arrival": [ 2, { "label" : "Arrival", "criterion" : "arrival", "expression" : self.username} ],
                                              },
        
                                      "app" : {
                                               "type": [ 0, { "label" : "Type", "criterion" : "type", "expression" : sorted(list(self.osci.get_list(obj_attr_list["cloud_name"], "GLOBAL", "ai_types")))} ],
                                               "arrival": [ 1, { "label" : "Arrival", "criterion" : "arrival", "expression" : "all"} ],
                                               },
                                      "aidrs" : {
                                                 "pattern": [ 0, { "label" : "Pattern", "criterion" : "pattern", "expression" : sorted(list(self.osci.get_list(obj_attr_list["cloud_name"], "GLOBAL", "aidrs_patterns")))} ],
                                                 "arrival": [ 1, { "label" : "Arrival", "criterion" : "arrival", "expression" : "all"} ],
                                               },
                                      
                                      }
                    else :
                        _view_dict = _result
        
                    _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Unable to get GLOBAL object list: " + _fmsg
                cberr(_msg)
                _view_dict = False

            else :
                _msg = obj_attr_list["object_type"] + " with the following "
                _msg += obj_attr_list["object_attribute"] + _msg_string[_list_name]
                _msg += "to this experiment (Cloud "
                _msg += obj_attr_list["cloud_name"]  + ") :\n" + _list
                cbdebug(_msg)

                if isinstance(_view_dict, set) :
                    _view_dict = sorted(list(_view_dict))
                if isinstance(_view_dict, list) :
                    _view_dict = sorted(_view_dict)
                    
            return self.package(_status, _msg, _view_dict)

    @trace
    def globalshow(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _result = []
            
            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)
 
                if not _status :
                    _list_name = obj_attr_list["object_type"].lower() + '_' + obj_attr_list["object_attribute"] + 's'

                    if obj_attr_list["attribute_name"] in list(self.osci.get_list(obj_attr_list["cloud_name"], "GLOBAL", _list_name)) :

                        _formatted_result = []
                        _object_contents = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, obj_attr_list["global_object"], False)

                        if obj_attr_list["global_object"] == "vm_templates" :
                            if obj_attr_list["attribute_name"] in _object_contents :
                                _result = str2dic(_object_contents[obj_attr_list["attribute_name"]])
                                for _key,_value in _result.items() :
                                    _formatted_result.append(_key + ": " + _value)
    
                        elif obj_attr_list["global_object"] == "ai_templates" or obj_attr_list["global_object"] == "aidrs_templates" :
                            for _key, _value in _object_contents.items() :
                                if _key.count(obj_attr_list["attribute_name"]) :
                                    _key = _key.replace(obj_attr_list["attribute_name"] + '_', '')
                                    # A trick to display the AI definition
                                    # in a specific order. It is ugly and not
                                    # efficient, but it will do for now.
                                    if _key == "sut" :
                                        _key = _key.replace(_key, "00___" + _key)
                                    elif _key == "load_manager_role" :
                                        _key = _key.replace(_key, "01___" + _key)
                                    elif _key == "metric_aggregator_role" :
                                        _key = _key.replace(_key, "02___" + _key)
                                    elif _key == "capture_role" :
                                        _key = _key.replace(_key, "03___" + _key)
                                    elif _key.count("setup") :
                                        _key = _key.replace(_key, "04___" + _key)
                                    elif _key.count("reset") :
                                        _key = _key.replace(_key, "05___" + _key)
                                    elif _key.count("start") :
                                        _key = _key.replace(_key, "06___" + _key)
                                    elif _key == "load_level" :
                                        _key = _key.replace(_key, "07___" + _key)
                                    elif _key == "load_duration" :
                                        _key = _key.replace(_key, "08___" + _key)

                                    elif _key == "type" :
                                        _key = _key.replace(_key, "00___" + _key)
                                    elif _key == "max_ais" :
                                        _key = _key.replace(_key, "01___" + _key)
                                    elif _key == "iait" :
                                        _key = _key.replace(_key, "02___" + _key)
                                    elif _key == "lifetime" :
                                        _key = _key.replace(_key, "09___" + _key)
                                                                                                                                                                                                                                                                                                                                
                                    _formatted_result.append(_key + ": " + _value)

                        _formatted_result.sort()

                        if obj_attr_list["global_object"] == "ai_templates" or obj_attr_list["global_object"] == "aidrs_templates" :
                            for _line_number in range(0, len(_formatted_result)) :
                                if _formatted_result[_line_number].count("___") :
                                    _formatted_result[_line_number] = _formatted_result[_line_number][5:]

                        _status = 0
                    else :
                        _status = 179
                        _fmsg = "Unknown " + obj_attr_list["object_type"] + ' '
                        _fmsg += obj_attr_list["object_attribute"] 
                        _fmsg += " (" + obj_attr_list["attribute_name"] + ")"
                        
        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Unable to get object: " + _fmsg
                cberr(_msg)
                _view_dict = False

            else :
                _msg = "The " + obj_attr_list["object_type"] + " with the "
                _msg += obj_attr_list["object_attribute"] + ' ' + obj_attr_list["attribute_name"]
                _msg += " has the following configuration on experiment (Cloud "
                _msg += obj_attr_list["cloud_name"]  + ") :\n" + '\n'.join(_formatted_result)
                cbdebug(_msg)

            return self.package(_status, _msg, _result)

    @trace
    def globalalter(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"
            _xfmsg = ''
            _result = {}

            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

                if not _status :
                    _obj_attrib, _obj_value = obj_attr_list["specified_kv_pair"].split('=')

                    _fields = [] 
                    _fields.append("|attribute                              ")
                    _fields.append("|old value                          ")
                    _fields.append("|new value                          ")

                    _p_obj_attrib = _obj_attrib.replace(obj_attr_list["specified_attribute"] + '_', '')

                    _smsg = "The attribute \"" + _p_obj_attrib + "\" on "
                    _smsg += obj_attr_list["specified_attribute"] + " "
                    _smsg += obj_attr_list["object_type"] 
                    _smsg += " was modified:\n"

                    _fmsg = "The attribute \"" + _p_obj_attrib + "\" on "
                    _fmsg += obj_attr_list["specified_attribute"]
                    _fmsg += obj_attr_list["object_type"] 
                    _fmsg += " could not be modified modified:\n"

                    _fmt_obj_chg_attr = ''.join(_fields) + '\n'

                    _old_values = self.osci.get_object(obj_attr_list["cloud_name"], "GLOBAL", False, \
                                                       obj_attr_list["global_object"], \
                                                       False)

                    if not _obj_attrib in _old_values :
                        _old_values[_obj_attrib] = "non-existent"

                    self.osci.update_object_attribute(obj_attr_list["cloud_name"], "GLOBAL", obj_attr_list["global_object"], \
                                                      False, _obj_attrib, _obj_value)

                    _fmt_obj_chg_attr += '|' + _obj_attrib.ljust(len(_fields[0]) - 1)
                    _fmt_obj_chg_attr += '|' + _old_values[_obj_attrib].ljust(len(_fields[1]) - 1)
                    _fmt_obj_chg_attr += '|' + _obj_value.ljust(len(_fields[2]) - 1)
                    _result["old_" + _obj_attrib] = _old_values[_obj_attrib]

                    _result[_obj_attrib] = _obj_value  
                    _smsg += _fmt_obj_chg_attr
    
                    _status = 0

        except self.ObjectOperationException, obj :
            _status = 8
            _xfmsg = str(obj.msg)

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 8
            _xfmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _xfmsg = str(e)

        finally :
            if _status :
                _msg = _fmsg + _xfmsg
                cberr(_msg)
            else :
                _msg = _smsg
                cbdebug(_msg)

            return self.package(_status, _msg, _result)

    @trace
    def expid(self, obj_attr_list, parameters, command) :
        '''
        TBD
        '''
        try :
            _status = 100
            _fmsg = "An error has occurred, but no error message was captured"

            _result = None 

            _status, _fmsg = self.parse_cli(obj_attr_list, parameters, command)

            if not _status :
                _status, _fmsg = self.initialize_object(obj_attr_list, command)

                if not _status :
                    if len(obj_attr_list["command"].split()) == 2 :
                        parameters = obj_attr_list["cloud_name"] + " time"
                        _status, _msg, _object = self.show_object({}, parameters, "cloud-show")
            
                        if not _status :
                            _msg = "Current experiment identifier is \"" 
                            _msg += _object["result"]["experiment_id"] + "\"."
                            _result = _object["result"]["experiment_id"]
            
                    else :
                        parameters = obj_attr_list["cloud_name"] + " time experiment_id=" + obj_attr_list["command"].split()[2]
                        _status, _msg, _object = self.alter_object(obj_attr_list, \
                                                                   parameters, \
                                                                   "cloud-alter")
            
                        if not _status :
                            _msg = "Experiment identifier was changed from \""
                            _msg += _object["result"]["old_experiment_id"] + "\" to \""
                            _msg += _object["result"]["experiment_id"] + "\". " 
        
                    _status = 0

        except self.osci.ObjectStoreMgdConnException, obj :
            _status = 8
            _fmsg = str(obj.msg)

        except Exception, e :
            _status = 23
            _fmsg = str(e)

        finally :
            if _status :
                _msg = "Unable to get EXPID object list: " + _fmsg
                cberr(_msg)
                _view_dict = False

            else :
                cbdebug(_msg)

            return self.package(_status, _msg, _result)
