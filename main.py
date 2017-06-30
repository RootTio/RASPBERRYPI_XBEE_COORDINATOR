#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#librerias

#IMPORTAR LIBRERIAS
import MySQLdb
import sys
import binascii
import time
from xbee import XBee,ZigBee
import serial
import signal
import threading
from termcolor import colored
#CONEXION A LA BASE DE DATOS
def hora():
	hora=time.strftime('%Y-%m-%d %H:%M:%S')
	return hora

def conn():
	try:
		print "Conectando a la base de datos...
		db= MySQLdb.connect(host= "XXX.XXX.XXX.XXX",user="XXX",passwd="XXX",db="XXX")
	except Exception as e:
		print("No ha entrado a la base de datos")
		conn()
	return db

#VARIABLES GLOBALES
nave="2"
tcancel=[]
tnodos=[]
init_time=time.time()
class TimeoutException(Exception):
	pass
def timeout_handler(signum,frame):
	raise TimeoutException

signal.signal(signal.SIGALRM, timeout_handler)
#FUNCIONES
def toint(list): #convierte un tupple a int
	s=''.join(map(str,list))
	return int(s)

def tostr(list):
        s=''.join(map(str,list))
        return s

def AddressNodos():# Lee todos los nodos en la nave
	time.sleep(0.1)
	db=conn()
	cur=db.cursor()
	cur.execute("SELECT nd.idnodo from nodos nd where idnave=%s group by nd.idnodo"%nave)
	conn().commit()
	time.sleep(0.1)
	tnodos=cur.fetchall()
	db.close()
	return tnodos

def readIdSen(stnodo): #Lee el tiempo de sensado por nodo
	db=conn()
	cur=db.cursor() 
	cur.execute("SELECT se.idsen from sensores se inner join nodos nd on nd.idnodo=se.idnodo where nd.idnave=%s and nd.idnodo=%s",(nave,stnodo))
        db.commit()
	time.sleep(0.1)
        tidnodo=cur.fetchall() #guarda el total de idsen por nodo
	db.close()
	return tidnodo

def readTimSen():
	nodos=AddressNodos()[0]
	stnodo=tostr(nodos)
	db=conn()
	cur=db.cursor()
	#un nodo perteneciente a la nave para identificar el tiempo de sensado por tipo de sensor
	cur.execute("SELECT se.tipo,se.timsen from sensores se inner join nodos nd on se.idnodo=nd.idnodo WHERE se.idnodo='%s' order by timsen asc"%(stnodo))
        db.commit()
	time.sleep(0.1)
        ttimsen=cur.fetchall()
	db.close()
	return ttimsen

def arrayToString(array):
	st=''.join(array)
	return st

def idSenXnodo():# Regresa una matriz con la direccion del nodo y los idsen que contiene cada nodo 
	addNodos=AddressNodos()
	lenNodos=len(addNodos)
	w,h=4,lenNodos
	ctrnodo=0
	IdSen=[[0 for x in range(w)]for y in range(h)]
	for nodo in addNodos:
		ctrnodo+=1
		stnodo=arrayToString(nodo)
		tidnodo=readIdSen(stnodo) #Todos los idsen por nodo
		lidsen=len(tidnodo)#Numero de idsen por nodo
		for x in range(0,lidsen):      
                	IdSen[ctrnodo-1][x]=stnodo,map(int,tidnodo[x])#Introduce idsen por nodo en una Matris
        return IdSen

def readDestAddrLong(): # LEE LAS DIRECCIONES DE LA BASE DE DATOS.
	DEST_ADDR_LONG=[]
	#tnodos=AddressNodos()
	#lnodos=len(tnodos)
 	#for x in range(0,lnodos):
        #	DEST_ADDR_LONG.append(parseMAC(tnodos[x]))
	DEST_ADDR_LONG.append("\x00\x13\xA2\x00\x41\x52\xEB\x60")
	return DEST_ADDR_LONG
				
def timSenXtipo(nsen): #LEE LOS TIEMPOS DE SENSADO Y LA DIRECCIÓN
	Vtimsen=[]
	ttimsen=readTimSen()
	for i in range(0,nsen):
        	for ts in ttimsen:
			Vtimsen.append((ts[0],ts[1]))	
	return Vtimsen

def parseXbeeData(nsen,data): # PARSEA LOS DATOS RECIVIDOS DE LOS NODOS Y LOS DIVIDE SEGUN EL NUMERO DE SENSORES
	start=2
	n=[]
	for z in range(0,nsen):
        	end=start+5
		n.append(data[start:end])
		n[z]=arrayToString(n[z])
		start+=6
	return n

def parseXbeeAddr(address):
	for x in range(0,8):
        	address[x]=hex(ord(address[x]))
                staddress=''.join(address)
                staddress=staddress.replace("0x0","0x00")
                staddress=staddress.replace("0x","")
                if(len(staddress)==15): # Si el ultimo par de digitos es de 1 solo numero
                	staddress=list(staddress)
                        staddress.append(staddress[14])
                        staddress[14]='0'
	return staddress

def wakeUpNodo(xbee,addr):
	xbee.send("tx",data="0",dest_addr_long=addr)
	for i in range(1):
		signal.alarm(30)
		rx="0"
		try:
			print "Desperdando al nodo","".join(parseXbeeAddr(map(str,addr)))
			rx=xbee.wait_read_frame()
			time.sleep(0.2)
			rx=xbee.wait_read_frame()
		except TimeoutException:
			continue
		else:
			signal.alarm(0)
		if(rx=="0"):
			print "XBEE NO CONECTADO"
	return rx

def parseMAC(address):
	x=arrayToString(map(str,binascii.unhexlify(tostr(address))))	
	return x

def parseType(nsen):
        Vtipo=timSenXtipo(nsen)
        tipo=[]
        for x in xrange(0,nsen):
                tipo.append(Vtipo[x][0])
	return tipo

def parseTim(nsen):
	#Lnodos=len(readDestAddrLong())
        Vtipo=timSenXtipo(nsen)
        #Vfinal=[]
	tim=[]
	#tipo=[]
	#ntim=[]
	#Vfinal.append(Vtipo[0][1])
	for x in xrange(0,nsen):
		tim.append(Vtipo[x][1])
		#tipo.append(Vtipo[x][0])
	#for z in xrange(0,nsen-1):
		#ntim.append(Vtipo[z+1][1])
		#Vfinal.append(ntim[z]-tim[z])
	return tim		

def work(dataT,tipo):
		Lnodos=len(dataT)
		for x in range(0,Lnodos):
			try:	
			
				address=dataT[x][0]
				n=dataT[x][1]
				print "subiendo"
				db=conn()
				cur=db.cursor()
				print "address",tostr(address),"valor = ",float(n[tipo-1]),"fecha =",hora()
				cur.execute("INSERT INTO sensornodo(idsen,valor,fecha) VALUES((SELECT idsen from sensores where idnodo=%s and tipo=%s),%s,%s)",(tostr(address),tipo,float(n[tipo-1]),hora()))
               			time.sleep(0.1)
				db.commit()
				db.close()
			except Exception as e:
				continue
		
def uploadData(dataT,nsen,past_time):
	tim=parseTim(nsen)
	tipo=parseType(nsen)
	now=time.time()-past_time
	for i in range(0,nsen):
		timer=threading.Timer(((tim[i]*60)-now)-(0.1*i+1),work,[dataT,tipo[i]])
		timer.start()			
		time.sleep(0.1) #requerido



def core():
	nsen=1
	#LEER LOS TIEMPOS DE SENSADO
	tim=parseTim(nsen)
	print tim

	
def XbeeData():
	past_time=time.time()
	ser=serial.Serial('/dev/serial0',9600,interCharTimeout=0.5)
        xbee=ZigBee(ser)
	dataT=[]
	n=0
	nsen=1
	try:	
		DEST_ADDR_LONG=readDestAddrLong()
                for jk in range(0,len(DEST_ADDR_LONG)):
			if len(DEST_ADDR_LONG)==1:
				time.sleep(2)
                	rx=wakeUpNodo(xbee,DEST_ADDR_LONG[jk])# Despierta al sensor
			if(rx!="0"):
                        	if(rx['id']=='rx'):
                        		dt=rx['rf_data']#selecciona el valor de rf_data
                                	adt=rx['source_addr_long']
                                	address=list(adt)
                                	data=list(dt) #convierte los datos a vector de caracteres
					n=parseXbeeData(nsen,data)
					ban=0
					address=parseXbeeAddr(address)
					for i in range(0,len(dataT)):
						if(dataT[i]==address):
							ban=1
					if(ban==0):		
						dataT.append((address,n))
					print arrayToString(address),n[0]
					alerta(n,nsen)	
				if(rx['id']!='rx'):
					print "NO SE HA ENCONTRADO EL NODO"
		ser.close()
		print "Procesos :",colored(threading.active_count(),"yellow")
		#print "Tiempo de proceso antes de subir datos",time.time()-past_time
		uploadData(dataT,nsen,past_time)
		tim=parseTim(nsen)
		for i in range(0,len(dataT)):
			print "Address",dataT[i][0]
		lost_time=time.time()-past_time
		print "tiempo de proceso",lost_time
		if((tim[0]*60)>lost_time): #Si no, no es necesario
			time.sleep((tim[0]*60)-lost_time)

	except KeyboardInterrupt:
        	sys.exit()
	#xbee.halt()
        #ser.close()

def alerta(n,nsen):
	z=[]
	dict = {'0': 'Temperatura', '1':'Humedad' , '2': 'Iluminacion','3':'PH'}
	for i in range(0,nsen):
		z.append(float(n[i]))
		print dict[str(i)],colored(z[i],"red")
		if(i==0):
			if(z[i]<=25):
				print "el valor de ",colored(dict[str(i)],"yellow")," está ",colored("abajo de lo normal","yellow")
			if(z[i]>=29):
				print "el valor de ",colored(dict[str(i)],"yellow")," está ",colored("arriba de lo normal","red")
			if(z[i]>25 and z[i]<29):
				print "el valor de ",colored(dict[str(i)],"yellow")," está ",colored("dentro de lo normal","green")
		#if(i==1):
		
		#if(i==2):
		
		#if(i==3):

#PROGRAMA PRINCIPAL
def main(): 
	while(1):
		#core()		                                     
		XbeeData()
if __name__== '__main__':
	main()

