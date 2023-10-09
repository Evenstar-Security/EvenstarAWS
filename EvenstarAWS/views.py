from django.shortcuts import render
from django.http import HttpResponse

def globalprotect(request):
	return(render(request,'globalprotect.html',{}))

def home(request):
	return(render(request,'home.html',{}))