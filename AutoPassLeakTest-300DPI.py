import RPi.GPIO as GPIO
import time
import io
from io import StringIO
import sys
from datetime import datetime
import zpl
import socket
import pyodbc

# GPIO pin to be used
ULsigPass = 5
ULsigFail = 6
# Defining which GPIO numbering scheme to use, how the pin will be used, and it's starting state
GPIO.setmode(GPIO.BCM)
GPIO.setup(ULsigPass, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(ULsigFail, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def PersistentDataCollect():
    global EmpID
    global WorkOrder
    global PtT
    print('\n')
    while True:
        try:
            EmpID = int(input('Enter your employee ID: '))
            if EmpID>0:
                break
            else:
                print('Please enter a valid employee number (Ex: 1234)')
                continue
        except ValueError:
            print('Please enter a valid employee number (Ex: 1234)')
            continue
        else:
            break
    while True:
        try:
            WorkOrder = int(input('Scan the work order: '))
            if WorkOrder>0:
                break
            else:
                print('Please scan the work order barcode at the top of the work order.')
                continue
        except ValueError:
            print('Please scan the work order barcode at the top of the work order.')
            continue
        else:
            break
    while True:
        try:
            PtT = int(input('Enter number of assemblies to test: '))
            if PtT>0:
                break
            else:
                print('Please enter a valid number.')
                continue            
        except ValueError:
            print('Please enter a valid number.')
            continue
        else:
            break
    print('Retrieving work order information.  Please wait.')
    return PersistentDataCollect
    

def DBQuery():
    global ATIPart
    global CustPart
    global CompList
    
    dsn = 'ATISdatasource'
    user = 'access87'
    password = 'ati'
    database = 'IERP87'

    conn_string = 'DSN=%s;UID=%s;PWD=%s;DATABASE=%s' % (dsn, user, password, database)
    conn = pyodbc.connect(conn_string, autocommit=True)
    cursor = conn.cursor()

    sql = "select IMA.IMA_ItemID, IMA.IMA_CustItemID, IMA.IMA_CustomerID, IMA.IMA_Classification, IMA.IMA_ItemName, WKO.WKO_StatusCode, WKO.WKO_WorkOrderID, WKO.WKO_WorkOrderTypeCode, WKO.WKO_StartDate, WKO.WKO_StartQty, PST_ALL.PST_CompItemID from iERP87.dbo.IMA IMA, iERP87.dbo.PST_ALL PST_ALL, iERP87.dbo.WKO WKO where IMA.IMA_ItemID = WKO.WKO_ItemID AND WKO.WKO_ItemID = PST_ALL.PST_ParentItemID AND ((IMA.IMA_Classification='Brazed Assembly') AND (IMA.IMA_ItemStatusCode='Active') AND (WKO.WKO_StatusCode='Released') AND (IMA.IMA_CustItemID Is Not Null) AND (PST_ALL.PST_CompItemID<>'NP') and WKO.WKO_WorkOrderID=?)"

    cursor.execute(sql, WorkOrder)
    row = cursor.fetchone()
    if row:
        ATIPart = (str(row.IMA_ItemID))
        CustPart = (str(row.IMA_CustItemID))
        print('\nATI Part number: ', (ATIPart))
        print('Customer Part number: ', (CustPart))

    cursor.execute(sql, WorkOrder)
    CompList = [column[10] for column in cursor.fetchall()]
    print('Component list from work order:\n', (CompList)) 


    disconn = conn.cursor()
    disconn.close()
    del disconn

    return DBQuery

def DataCollect():
    global Part1
    global Part2
    global CurrentDT

    print('\n')
    while True:
        try:
            Part1 = str(input('Scan part #1 of assembly: '))
            if any( [PartNum in Part1 for PartNum in CompList] ):
                    print("This is a correct part!")
                    break
            else:
                print('Please scan correct part or see manager for assistance.')
        except ValueError:
            print('Please rescan part #1.')
            continue
    Part1 = Part1.replace('~', '_7e') #Changes the ~ to hex for the ZPL code to translate correctly.
    Part1 = Part1.replace('>', '_3e')
    Part1 = Part1.replace('.', '_2e')
    Part1 = Part1.replace('[', '_5b')
    Part1 = Part1.replace(')', '_29')
    while True:
        try:
            Part2 = str(input('Scan part #2 of assembly: '))
            if any( [PartNum in Part2 for PartNum in CompList] ):
                    print("This is a correct part!")
                    break
            else:
                print('Please scan correct part or see manager for assistance.')
        except ValueError:
            print('Please rescan part #2.')
            continue
    Part2 = Part2.replace('~', '_7e')
    Part2 = Part2.replace('>', '_3e')
    Part2 = Part2.replace('.', '_2e')
    Part2 = Part2.replace('[', '_5b')
    Part2 = Part2.replace(')', '_29')
    print('\n')

    CurrentDT = (datetime.now().strftime("%Y-%m-%d/%H-%M-%S"))   
    
    return DataCollect

def SignalDetect():
    if GPIO.input(ULsigPass) == GPIO.HIGH:
        print('Start leak test now')
        #GPIO.wait_for_edge(ULsigPass, GPIO.FALLING, bouncetime=200)
        print('Leak test started')
        #time.sleep(5)
    if GPIO.input(ULsigFail) == GPIO.HIGH:
        print('Start leak test now')
        GPIO.wait_for_edge(ULsigFail, GPIO.FALLING, bouncetime=200)
        print('Leak test started')
        #time.sleep(5)
    if (GPIO.input(ULsigPass) == GPIO.LOW) and (GPIO.input(ULsigFail) == GPIO.LOW):
        print('\nWaiting for leak test to complete\n') 
#time.sleep(20) #Per Daniel, this allows time for sniffer
    GPIO.remove_event_detect(ULsigPass)
    GPIO.remove_event_detect(ULsigFail)

    return SignalDetect

def DigitCheck():

    global CheckDigit # CheckDigit number

    numbers=[] # Results after encoding
    sum=0
    
    var=(str(ATIPart) + str(CustPart) + str(CurrentDT)).lower() # string for all letters
    for letter in var:
        if letter.isnumeric():
            numbers.append(int(letter))
            #print(letter,'is numeric is',letter.isnumeric())

        elif letter.islower():
            number=ord(letter)-96
            numbers.append(number)
            #print(letter,'lower is',letter.islower())
        else:
            numbers.append(1)

    for i in range(len(numbers)):
        sum=sum+(i+1)*numbers[i]
        #print(sum)
    
    CheckDigit=(sum+(len(numbers)%2))%10
    #print(var)
    print('check digit is',CheckDigit)

    return DigitCheck


def CreateBarcode():
    GPIO.input(ULsigPass) == GPIO.HIGH
#    GPIO.add_event_detect(ULsigFail, GPIO.RISING, bouncetime=200)
#    GPIO.add_event_detect(ULsigPass, GPIO.RISING, bouncetime=200)

    while True:
        if GPIO.event_detected(ULsigFail):
            print('Leak test failed\n')
            break

        #if GPIO.event_detected(ULsigPass):
        if GPIO.input(ULsigPass) == GPIO.HIGH:
                print('Leak Test Successful.\n')
                old_stdout = sys.stdout
                new_stdout = io.StringIO()
                sys.stdout = new_stdout
                print(ATIPart, CustPart, CurrentDT, CheckDigit, sep='~') 
                MBC = new_stdout.getvalue()
                sys.stdout = old_stdout
                MBC = MBC.replace('~', '_7e')
                print('Master Barcode Information after converting special characters \n', (MBC)) #Shows what the barcode info will be
                l = zpl.Label(100,60)

                height = 7
                l.origin(17,height)
                l.write_text('ATI PN: ' + str(ATIPart), char_height=3, char_width=3, line_width=40, justification='L')
                l.endorigin()

                height += 3
                l.origin(17,height)
                l.write_text('ATI WO: ' + str(WorkOrder), char_height=3, char_width=3, line_width=40, justification='L')
                l.endorigin()

                height += 3
                l.origin(17,height)
                l.write_text('Cust PN: ' + CustPart, char_height=3, char_width=3, line_width=40, justification='L')
                l.endorigin()

                l.origin(2.5, 6)
                l.write_barcode(height=4, barcode_type='Q', magnification=3)
                l.write_text(MBC)
                l.endorigin()

                height += 3
                l.origin(17, height)
                l.write_text(datetime.now().isoformat(sep='/', timespec='minutes'), char_height=3, char_width=3, line_width=40, justification='L')
                l.endorigin()

                height = 7
                l.origin(42,height)
                l.write_text('ATI PN: ' + str(ATIPart), char_height=3, char_width=3, line_width=40, justification='R')
                l.endorigin()

                height += 3
                l.origin(42,height)
                l.write_text('ATI WO: ' + str(WorkOrder), char_height=3, char_width=3, line_width=40, justification='R')
                l.endorigin()

                height += 3
                l.origin(42,height)
                l.write_text('Cust PN: ' + CustPart, char_height=3, char_width=3, line_width=40, justification='R')
                l.endorigin()

                l.origin(84, 6)
                l.write_barcode(height=4, barcode_type='Q', magnification=3)
                l.write_text(MBC)
                l.endorigin()

                height += 3
                l.origin(42, height)
                l.write_text(datetime.now().isoformat(sep='/', timespec='minutes'), char_height=3, char_width=3, line_width=40, justification='R')
                l.endorigin()

                old_stdout = sys.stdout
                new_stdout = io.StringIO()
                sys.stdout = new_stdout
                print(l.dumpZPL())
                zpl_convert = new_stdout.getvalue()
                sys.stdout = old_stdout
                zpl_convert = zpl_convert.replace('BQN,2,3,Q,7^FD', 'BXN,7,200,0,0,1,_^FH_^FD')
                print('Raw info sent to printer:\n', (zpl_convert)) #Shows what ZPL data is sent to the printer
            
                mysocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                #host = "192.168.8.97" #Monterrey printer
                #host = "192.168.5.166" #Springdale Dev printer
                port = 9100   
                try:           
                    mysocket.connect((host, port)) #connecting to host
                    mysocket.send(zpl_convert.encode('ascii')) #ZPL output being sent to the printer
                    mysocket.close () #closing connection
                except:
                    print("Error with printer connection")
                    e = sys.exc_info()[0]
                    print(e)
                    time.sleep(3)
                break
    return CreateBarcode

def Main():
    DBQuery()
    DataCollect()
    SignalDetect()
    DigitCheck()
    CreateBarcode()
    
PersistentDataCollect()
for x in range(0, PtT):
    Main()
    x += 1