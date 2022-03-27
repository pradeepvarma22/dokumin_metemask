from django.db import models
import os

def get_file_path(instance, filename):
    ext = filename.split('.')[-1]
    layerPath = './images/'+str(instance)
    filename_start = filename.replace('.'+ext,'')

    filename = "%s.%s" % (filename_start, ext)
    return os.path.join(layerPath, filename)


class Certifier(models.Model):
    name = models.CharField(max_length=255,null=True,blank=True)
    address =models.CharField(max_length=255,null=True,blank=True)
    moralisid = models.CharField(max_length=255,null=True,blank=True)
    
    def __str__(self):
        return self.moralisid or ''

class Receiver(models.Model):
    name = models.CharField(max_length=255,null=True,blank=True)
    certifier =  models.ForeignKey(Certifier,on_delete=models.CASCADE)
    course = models.CharField(max_length=255,null=True,blank=True)
    address =models.CharField(max_length=255,null=True,blank=True)
    image = models.ImageField(upload_to=get_file_path,verbose_name=(u'File'))
    
    def __str__(self):
        return self.name or ''

class ProjectDesc(models.Model):
    certifier = models.ForeignKey(Certifier, null=True, on_delete= models.SET_NULL)
    proj_name = models.CharField(max_length=255,null=True,blank=True)
    proj_desc = models.TextField(null=True,blank=True)
    symbol = models.CharField(max_length=50,null=True,blank=True)
    img_hash = models.CharField(max_length=255,null=True,blank=True)
    meta_hash = models.CharField(max_length=255,null=True,blank=True)

    def __str__(self):
        return self.proj_name or ''