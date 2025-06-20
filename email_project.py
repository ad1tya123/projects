import smtplib
import speech_recognition as sr
import pyaudio
from email.message import EmailMessage
listner=sr.Recognizer()


def get_voice_info():
    try:
        with sr.Microphone() as source:
            print("Speak Something I am Listening.........")
            voice=listner.listen(source)
            info=listner.recognize_google(voice).lower()
            print(info)
            return info
    except:
         pass

def send_email(reciver,subject,message):
    server=smtplib.SMTP('smtp.gmail.com',587)
    server.starttls()
    server.login('glennfernandes111@gmail.com','igne pcap ewpr hrcc')
    email = EmailMessage()
    email['From']='glennfernandes111@gmail.com'
    email['To']=reciver
    email['Subject']=subject
    email.set_content(message)
    server.send_message(email)

email_list={'glenn':'glennfernandes23aiml@rnsit.ac.in',
      'darshan':'darshanb23aiml@rnsit.ac.in',
      'charan':'charanrajv23aiml@rnsit.ac.in',
      'aditya':'adityabenkal23aiml@rnsit.ac.in',
      'nisha':'nishajbritto1971@gmail.com'
    }

def get_mail_info():
    print("To Whom you wanna send email \n (Name of the person): ")
    name=get_voice_info()


    if name in email_list.keys():
        reciver=email_list[name]
        print(reciver)

    else:
        print("Users Email Not found try again ")
        exit()

    print("What is the subject of the mail: ")
    subject=get_voice_info().capitalize()

    print("What is the Message :")
    message=get_voice_info()

    print("==========Email Info===========")
    print("TO=",reciver)
    print("SUBJECT=",subject)
    print("Message=",message)

    print("ARE YOU SURE YOU WANT TO SEND THIS MAIL (yes/no) ")
    send_more_email=input()
    if 'yes' in send_more_email:
        send_email(reciver,subject,message)
        print("YOUR MAIL HAS BEEN SENT ")
    else:
        print("YOU WANT TO RE-WRITE THE MAIL (YES/NO): ")
        rewrite=input()
        if 'yes' in rewrite:
            get_mail_info()
        else:
            exit()



get_mail_info()

