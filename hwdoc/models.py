# -*- coding: utf-8 -*- vim:encoding=utf-8:
# vim: tabstop=4:shiftwidth=4:softtabstop=4:expandtab

# Copyright © 2010-2012 Greek Research and Technology Network (GRNET S.A.)
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND ISC DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS. IN NO EVENT SHALL ISC BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT,
# OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF
# USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
# TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
'''
hwdoc module's functions documentation. Main models are Equipment and ServerManagement 
'''

from django.db import models
from django.db.utils import DatabaseError

# Allocation models #
class Email(models.Model):
    '''
    Email Model. Represents an email. No special checks are done for user input
    '''

    email = models.CharField(max_length=80)

    def __unicode__(self):
        return self.email

class Phone(models.Model):
    '''
    Phone Model. Represents a phone. No special checks are done for user input
    '''

    number = models.CharField(max_length=80)

    def __unicode__(self):
        return self.number

class Person(models.Model):
    '''
    Person Model. Represents a Person with relations to Email, Phone
    No special checks are done for user input
    '''

    name = models.CharField(max_length=80)
    surname = models.CharField(max_length=80)
    emails = models.ManyToManyField(Email)
    phones = models.ManyToManyField(Phone)

    def __unicode__(self):
        result =  '%s %s ' % (self.name, self.surname)
        if self.emails.count() > 0:
            result += '<%s> ' % ', '.join(map(lambda x: x[0], self.emails.values_list('email')))
        if self.phones.count() > 0:
            result += '%s' % ', '.join(map(lambda x: x[0], self.phones.values_list('number')))
        return result

class Project(models.Model):
    '''
    Project Model. The idea is to allocate Equipments to Projects
    '''

    name = models.CharField(max_length=80)
    contacts = models.ManyToManyField(Person, through='Role')

    def __unicode__(self):
        return self.name

class Role(models.Model):
    '''
    Roles for projects
    '''

    ROLES = (
                ('manager', 'Manager' ),
                ('technical', 'Techinal Person'), 
            )
    role = models.CharField(max_length=80, choices=ROLES)
    project = models.ForeignKey(Project)
    person = models.ForeignKey(Person)

    def __unicode__(self):
        return 'Project: %s, Person: %s %s, Role: %s' % (self.project.name, self.person.name, self.person.surname, self.role)

# Equipment models #
class Vendor(models.Model):
    '''
    Equipments have Models and belong to Vendors
    '''

    name = models.CharField(max_length=80)

    def __unicode__(self):
        return self.name

class Model(models.Model):
    '''
    Abstract class for all vendor models
    '''

    vendor = models.ForeignKey(Vendor)
    name = models.CharField(max_length=80)

    class Meta:
        abstract = True

    def __unicode__(self):
        return "%s %s" % (self.vendor, self.name)

class EquipmentModel(Model):
    '''
    Equipments have Models
    '''

    u = models.PositiveIntegerField(verbose_name="Us")

    def __unicode__(self):
        return "%s %s" % (self.vendor, self.name)

class Equipment(models.Model):
    '''
    Equipment model
    '''

    model = models.ForeignKey(EquipmentModel)
    allocation = models.ForeignKey(Project, null=True, blank=True)
    serial = models.CharField(max_length=80)
    rack = models.PositiveIntegerField(null=True, blank=True)
    unit = models.PositiveIntegerField(null=True, blank=True)
    purpose = models.CharField(max_length=80, null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    added = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        out = ""
        if self.purpose:
            out += "%s, " % self.purpose
        out += "%s " % self.model
        if self.rack and self.unit:
            out += "@ R%.2dU%.2d " % (self.rack, self.unit)
        out += "(%s)" % self.serial
        return out

class ServerManagement(models.Model):
    ''' 
    Equipments that can be managed have a ServerManagement counterpanrt
    '''

    equipment = models.OneToOneField(Equipment)
    METHODS = (
            ('ilo2', 'HP iLO 2'),
            ('ilo3', 'HP iLO 3'),
            ('irmc', 'Fujitsu iRMC'),
            ('ipmi', 'Generic IPMI'),
            ('dummy', 'Dummy Method Backend'),
        )
    method = models.CharField(choices=METHODS, max_length=10)
    added = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    hostname = models.CharField(max_length=80)
    username = models.CharField(max_length=80, null=True, blank=True)
    password = models.CharField(max_length=80, null=True, blank=True)
    license = models.CharField(max_length=80, null=True, blank=True)
    raid_license = models.CharField(max_length=80, null=True, blank=True)
    mac = models.CharField(max_length=17, null=True, blank=True)

    def __unicode__(self):
        return "%s for %s" % (self.get_method_display(), self.equipment)

    def __sm__(self, action, username, password, **kwargs):
        if username is None:
            username = self.username
        if password is None:
            password = self.password
        if action == 'license_set' and ( 'license' not in kwargs or kwargs['license'] is None):
            kwargs['license'] = self.license

        try:
            sm = __import__('hwdoc.vendor.' + self.method, fromlist=['hwdoc.vendor']) 
        except ImportError as e:
            # TODO: Log the error. For now just print 
            print e
            return
        
        try:
            return getattr(sm, action)(self.hostname, username, password, **kwargs)
        except AttributeError as e:
            # TODO: Log the error. For now just print 
            print e
            return

    def power_on(self, username=None, password=None):
        '''
        Power on a server
        '''

        return self.__sm__('power_on', username, password)

    def power_off(self, username=None, password=None):
        '''
        Power off a server
        '''

        return self.__sm__('power_off', username, password)

    def power_cycle(self, username=None, password=None):
        '''
        Power cycle a server
        '''

        return self.__sm__('power_cycle', username, password)

    def power_reset(self, username=None, password=None):
        '''
        Power reset a server
        '''

        return self.__sm__('power_reset', username, password)

    def power_off_acpi(self, username=None, password=None):
        '''
        Power off by sending an ACPI signal
        '''

        return self.__sm__('power_off_acpi', username, password)

    def pass_change(self, username=None, password=None, **kwargs):
        '''
        Change password for an OOB account
        '''

        if 'change_username' not in kwargs or 'newpass' not in kwargs:
            raise RuntimeError('Username and/or password to be changed not given')
        return self.__sm__('pass_change', username, password, **kwargs)

    def set_settings(self, username=None, password=None, **kwargs):
        '''
        Set OOB settings
        '''

        return self.__sm__('set_settings', username, password, **kwargs)

    def set_ldap_settings(self, username=None, password=None, **kwargs):
        '''
        Set OOB LDAP Settings
        '''

        return self.__sm__('set_ldap_settings', username, password, **kwargs)

    def boot_order(self, username=None, password=None, **kwargs):
        '''
        Set Boot order. One time boot if support can be enabled
        '''

        return self.__sm__('boot_order', username, password, **kwargs)

    def license_set(self, username=None, password=None, **kwargs):
        '''
        Set license for OOB if applicable
        '''

        return self.__sm__('license_set', username, password, **kwargs)

    def bmc_reset(self, username=None, password=None, **kwargs):
        '''
        Reset a BMC 
        '''

        return self.__sm__('bmc_reset', username, password, **kwargs)

    def bmc_factory_defaults(self, username=None, password=None, **kwargs):
        '''
        Reset a BMC to factory defaults
        '''

        return self.__sm__('bmc_factory_defaults', username, password, **kwargs)
