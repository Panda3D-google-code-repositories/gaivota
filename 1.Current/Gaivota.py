'''
GAIVOTA
Jogo criado para COS600 - Animacao e Jogos | ECI UFRJ
Marco ~ Julho de 2010

Authors: Filipe Yamamoto, Fabio Castanheira, Miguel Fernandes
Site: http://code.google.com/p/gaivota/
Blog: http://gaivotagame.blogspot.com
Version: 0.057 (Pre-Alpha)

Check out our site to see project details
'''
#----------------------------------------------------------------------------------------
from direct.showbase import DirectObject
from direct.showbase import Audio3DManager
from direct.gui.DirectGui import *
from direct.gui.OnscreenText import OnscreenText
from direct.gui.OnscreenImage import OnscreenImage
from direct.task import Task
from direct.interval.IntervalGlobal import *
from direct.particles.Particles import Particles
from direct.particles.ParticleEffect import ParticleEffect
from pandac.PandaModules import *
from pandac.PandaModules import loadPrcFile
from pandac.PandaModules import TransparencyAttrib

import direct.directbase.DirectStart
import random
import math
import sys

loadPrcFile("cfg.prc")

class Environment(DirectObject.DirectObject): #Class environment for construct environment
    def __init__(self): #Class constructor
        print "Loading (Level)"
        # add light
        dlight = DirectionalLight('my dlight')
        dlight.setColor(VBase4(1, 1, 1, 1))
        dlnp = render.attachNewNode(dlight)
        dlnp.setHpr(318, 216, 0)
        
        alight = AmbientLight('my alight')
        alight.setColor(VBase4(1, 1, 1, 1))
        alnp = render.attachNewNode(alight)
        
        render.setLight(alnp)
        render.setLight(dlnp)
     
        '''
        # add sky             
        self.sky = loader.loadModel("sky")
        self.sky.reparentTo(base.camera)
        self.sky.setEffect(CompassEffect.make(render)) 
        self.sky.setScale(5000)
        self.sky.setShaderOff()
        self.sky.setLightOff()
        # add the task for sky updates
        taskMgr.add(self.updateSky, 'updateSky-task')
        '''
        
        # setup rock texture and material
        myMaterial = Material()
        myMaterial.setShininess(22.0)
        myMaterial.setSpecular(VBase4(0.2,0.2,0.2,0.2))
        
        normalMapts = TextureStage('ts')
        normalMapts.setMode(TextureStage.MNormal)
        bumbTexture = loader.loadTexture("240-normal.jpg")
        bumbTexture.setMinfilter(Texture.FTLinearMipmapLinear)
        
        #incluir lixeira
        Lixeira((550,100,0))
        
        #incluir duto de ar
        dutoAr((700,1000,0))
        
        
        # create a main NodePath for all rocks, so we can use flatten, to speed things up
        self.rocks = NodePath("rocks")
        self.rocks.reparentTo(render)
        self.rocks.flattenStrong()
        self.rocks.setShaderAuto()
        self.rocks.setTexture(normalMapts, bumbTexture)
        self.rocks.setMaterial(myMaterial)
        
        
        #-------------------------------------------------------------------------------        
        self.ball = loader.loadModel("sala2")
        grassTexture = loader.loadTexture("grass1.jpg")
        self.ball.setTexture(grassTexture)
        self.ball.setShaderAuto()
        self.ball.reparentTo(self.rocks)
        self.ball.setScale(4,4,4)
        self.ball.setPos(0,0,0)
        self.ballCol = self.ball.copyTo(render)
        self.ballCol.hide()
        # this flag will let the collision system treat collision test for objects colliding into the terrain
        # since the terrain has no collisionNode attached, it is necessary to set the mask
        self.ballCol.setCollideMask(BitMask32.allOn())
        self.ballCol.flattenLight()
        #-------------------------------------------------------------------------------
        
class Player(object, DirectObject.DirectObject): #Class Player for the airplane
    def __init__(self): #Class constructor
        self.node = 0 #the player main node
        self.modelNode = 0 #the node of the actual model
        self.cNode = 0 #the player collision node attached to node
        self.cNodePath = 0 #node path to cNode
        self.contrail = ParticleEffect() #QUANDO BATE, CRIA EFEITO (LINHA DE BAIXO TB)
        self.contrail.setTransparency(TransparencyAttrib.MDual)
        self.contrail2 = ParticleEffect() #QUANDO ACIONA TURBO, CRIA EFEITO (LINHA DE BAIXO TB)
        self.contrail2.setTransparency(TransparencyAttrib.MDual)
        self.landing = False
        self.freeLook = False
        self.speed = 10
        self.speedMax = 100
        self.agility = 3
        self.HP = 10
        self.collisionHandler = CollisionHandlerEvent() # the collision handlers
        self.collisionHandlerQueue = CollisionHandlerQueue()
        self.zoom = -5
        self.gnodePath = 0 #node to phisics
        self.gNode = 0 #node of gravity
        self.gNodePath = 0#node path to actorNode
        self.msg = MessageManager()       
        self.roll = 0
        self.camHeight = 0
        
        base.win.movePointer(0, base.win.getXSize()/2, base.win.getYSize()/2)
        
        self.myImage=OnscreenImage(image = 'cursor.png', pos = (0, 0, -0.02), scale=(0.05))
        self.myImage.setTransparency(TransparencyAttrib.MAlpha)

        self.loadModel()
        self.addCamera()
        self.addEvents()
        self.addCollisions()
        self.addSound()
        
        self.moveTask = taskMgr.add(self.moveUpdateTask, 'move-task')
        self.mouseTask = taskMgr.add(self.mouseUpdateTask, 'mouse-task')
        self.zoomTaskPointer = taskMgr.add(self.zoomTask, 'zoom-task')
    def loadModel(self):#Function to load models and set physics
        #node path for player
        self.node = NodePath('player')
        self.node.setPos(1000,1000,200)
        self.node.reparentTo(render)
        self.node.lookAt(0,0,200)
        
        self.modelNode = loader.loadModel('gaivota')
        self.modelNode.reparentTo(self.node)
        self.modelNode.setScale(0.3)
        playerMaterial = Material()
        playerMaterial.setShininess(22.0) #Make this material shiny
        playerMaterial.setAmbient(VBase4(1,1,1,1))
        playerMaterial.setSpecular(VBase4(0.7,0.7,0.7,0.7))
        self.modelNode.setMaterial(playerMaterial)
        self.modelNode.setShaderAuto()
        
        self.aimNode = NodePath('aimNode')
        self.aimNode.reparentTo(self.node)
        self.aimNode.setPos(0,15,2)
    
        #gravity (aceleration 9.82)
        self.gravityFN=ForceNode('world-forces')
        self.gravityFNP=render.attachNewNode(self.gravityFN)
        self.gravityForce=LinearVectorForce(0,0,-9.82/8) 
        self.gravityFN.addForce(self.gravityForce)
        
        #add gravity to engine
        base.physicsMgr.addLinearForce(self.gravityForce)
        
        #Physics node
        self.gnodePath = NodePath(PandaNode("physics"))
        self.gNode = ActorNode("plane-actornode")
        self.gNodePath = self.gnodePath.attachNewNode(self.gNode)
        
        #object weigth
        self.gNode.getPhysicsObject().setMass(0.004)
        
        #add gravity force
        base.physicsMgr.addLinearForce(self.gravityForce)
        base.physicsMgr.attachPhysicalNode(self.gNode)
        
        #render object with physics
        self.gnodePath.reparentTo(render)
        self.node.reparentTo(self.gNodePath)  
    def addCamera(self): #Function that add camera to airplane
        base.disableMouse()
        base.camera.reparentTo(self.node)
        base.camera.setPos(0,self.zoom,2)
        base.camera.lookAt(self.aimNode)
    def addEvents(self):#Functions for airplane events
        self.accept( "wheel_up" , self.evtSpeedUp )
        self.accept( "wheel_down" , self.evtSpeedDown )
        self.accept('hit',self.evtHit)
        self.accept('f',self.evtFreeLookON)
        self.accept('f-up',self.evtFreeLookOFF)
        self.accept('mouse3',self.evtBoostOn)
        self.accept("menuOpen", self.evtMenuOpen)
        self.accept("menuClosed", self.evtMenuClose)
    def addCollisions(self): #Functions that add collisions for the airplane
        self.cNode = CollisionNode('player')
        self.cNode.addSolid(CollisionSphere(0,0,0,2.3))
        self.cNodePath = self.node.attachNewNode(self.cNode)
        self.cNodePath.show()
        
        base.cTrav.addCollider(self.cNodePath, self.collisionHandler)
        
        #raio de colisao:
        self.cNodeRay = CollisionNode('playerDuto')
        self.cNodeRay.addSolid(CollisionRay(0,0,-1 , 0,0,-1))
        self.cNodePathRay = self.node.attachNewNode(self.cNodeRay)
        self.cNodePathRay.show()
        base.cTrav.addCollider(self.cNodePathRay, self.collisionHandler)
        
        self.collisionHandler.addInPattern('hit')
        self.cNode.setIntoCollideMask(0);
        self.cNodeRay.setIntoCollideMask(0);      
    def addSound(self): #Function to add sound to airplane
        self.engineSound = loader.loadSfx("engine.mp3")
        self.engineSound.setLoop(True)
        self.engineSound.play()
        self.engineSound.setVolume(2.0)
        self.engineSound.setPlayRate(0)
        
        #Add environment music
        self.MusicSound = loader.loadSfx("warm-interlude.mp3")
        self.MusicSound.setLoop(True)
        self.MusicSound.play()
        self.MusicSound.setVolume(1.5)
        self.MusicSound.setPlayRate(1)
    def deleteTask(self, task): #Function to delete task
        self.__del__()
        return task.done   
    def mouseUpdateTask(self,task): #Function that update mouse moviments
        md = base.win.getPointer(0)
        x = md.getX()
        y = md.getY()
        deltaX = 0
        deltaY = 0
        if base.win.movePointer(0, base.win.getXSize()/2, base.win.getYSize()/2):
            deltaX = (x - base.win.getXSize()/2) *0.06 #* globalClock.getDt() *70 #* self.agility * (0.5+abs(self.roll)/50)
            deltaY = (y - base.win.getYSize()/2)*0.06 
            if deltaX > self.agility:
                deltaX = self.agility
            if deltaX < -self.agility:
                deltaX = -self.agility
            if deltaY > self.agility:
                deltaY = self.agility
            if deltaY < -self.agility:
                deltaY = -self.agility
            
            # don't move ship while in freelook mode
            if not self.freeLook:
                self.node.setH(self.node.getH() - deltaX)            
                self.node.setP(self.node.getP() - deltaY)
             
        # don't move ship while in freelook mode
        if not self.freeLook:
            self.roll += deltaX 
            self.camHeight += deltaY
            
        self.roll *= 0.95 #/ (globalClock.getDt() * 60)#* globalClock.getDt() * 700
        self.camHeight  *= 0.95 #* globalClock.getDt() * 700
        
        if self.roll < -25 * self.speed/self.speedMax:
            self.roll = -25 * self.speed/self.speedMax
        if self.roll > 25 * self.speed/self.speedMax:
            self.roll = 25 * self.speed/self.speedMax
        
        
        
        self.node.setR(self.roll*3)
        base.camera.setZ(2-self.camHeight*0.5* self.speed/self.speedMax)
        base.camera.lookAt(self.aimNode)
        base.camera.setR(-self.roll*2)
        #base.camera.setY(-30+self.speed/10)
        #base.camera.setX(self.roll*0.5)
        
        # freelook mode:
        if self.freeLook:
            self.camRotH -= deltaX *3
            self.camRotV -= deltaY *3
            if self.camRotV < 1:
                self.camRotV = 1
            if self.camRotV > 179:
                self.camRotV = 179
            
            base.camera.setX( math.cos(math.radians(self.camRotH))*math.sin(math.radians(self.camRotV)) *30 )
            base.camera.setY( math.sin(math.radians(self.camRotH))*math.sin(math.radians(self.camRotV)) *30 )
            base.camera.setZ( math.cos(math.radians(self.camRotV)) *30 )
            base.camera.lookAt(self.node)
            
            
        return task.cont
    
    #------------------------------------------------------------------------------------------------------
    #Function that update players position
    #------------------------------------------------------------------------------------------------------
    def moveUpdateTask(self,task): 
        # move where the keys set it
        self.node.setPos(self.node,Vec3(0,1.0*globalClock.getDt()*self.speed,0))
        
        #self.node.setPos(self.node,self.strafe*globalClock.getDt()*self.speed)
        return task.cont  
    def explode(self): #Function that control the explosion of the airplane
        self.ignoreAll()
        self.cNode.setIntoCollideMask(BitMask32.allOff())
        taskMgr.remove(self.moveTask)
        taskMgr.remove(self.mouseTask)
        taskMgr.remove(self.zoomTaskPointer)
        self.moveTask = 0
        self.mouseTask = 0
        
        if self.contrail != 0:
            self.contrail.cleanup()
        self.modelNode.hide()
        
        self.contrail = ParticleEffect()
        self.contrail.loadConfig('media/explosion.ptf')
        self.contrail.start(self.node)
        self.contrail.setLightOff()
        self.contrail2.cleanup()
        
        #add explosion sound
        self.audio3d = Audio3DManager.Audio3DManager(base.sfxManagerList[0], base.camera)
        self.audio3d.setDropOffFactor(0.2)
        self.Sound = self.audio3d.loadSfx('explosion.mp3')
        self.audio3d.detachSound(self.Sound)
        self.audio3d.attachSoundToObject( self.Sound, self.node )
        self.Sound.play()
        
        self.deleteTask = taskMgr.doMethodLater(4, self.deleteTask, 'delete task')
    def beatLevel(self): #Function that control the explosion of the airplane
        self.ignoreAll()
        self.cNode.setIntoCollideMask(BitMask32.allOff())
        taskMgr.remove(self.moveTask)
        taskMgr.remove(self.mouseTask)
        taskMgr.remove(self.zoomTaskPointer)
        self.moveTask = 0
        self.mouseTask = 0
        
        #add explosion sound
        self.audio3d = Audio3DManager.Audio3DManager(base.sfxManagerList[0], base.camera)
        self.audio3d.setDropOffFactor(0.2)
        self.Sound = self.audio3d.loadSfx('FF7Fanfare.mp3')
        self.audio3d.detachSound(self.Sound)
        self.audio3d.attachSoundToObject( self.Sound, self.node )
        self.Sound.play()
        
        self.deleteTask = taskMgr.doMethodLater(4, self.deleteTask, 'delete task')     
    def zoomTask(self, task): #Function for zoom
        if base.camera.getY() != self.zoom and self.freeLook == False:
            base.camera.setY( base.camera.getY()+ (self.zoom- base.camera.getY())*globalClock.getDt()*2 )
        return task.cont
    def evtBoostOn(self): #Function that increase speed 
        #taskMgr.remove(self.mouseTask)
        self.ignore( "wheel_up")
        self.ignore( "wheel_down")
        self.ignore('f')
        self.ignore('f-up')
        self.accept('mouse3-up',self.evtBoostOff)
        self.speed +=200
        #self.textSpeed.setText('Speed: '+str(self.speed))
        self.contrail2.loadConfig('media/contrail-boost.ptf')
        self.contrail2.start(self.node)
        self.zoom = -25
        self.evtFreeLookOFF()
    def evtBoostOff(self): #Function that decrease speed
        self.speed -=200
        #self.textSpeed.setText('Speed: '+str(self.speed))
        self.ignore('mouse3-up')
        self.addEvents()
        #self.mouseTask = taskMgr.add(self.mouseUpdateTask, 'mouse-task')
        #self.contrail.loadConfig('../../media/contrail.ptf')
        self.contrail2.softStop()
        self.zoom = -5-(self.speed/10)  
    def evtHit(self, entry): #Function that controls the event when the airplane hit something
        print "INTO " + entry.getIntoNodePath().getName()
        print "FROM " + entry.getFromNodePath().getName()
        print "PARENT " + entry.getIntoNodePath().getParent().getName()

        if entry.getFromNodePath().getName() == "playerDuto":
            if entry.getIntoNodePath().getName() == "duto": #Plane entering Finish area
                print "VENTO"
                self.msg.addMessage("ENTROU NO VENTO", 1)

        if entry.getFromNodePath().getName() == self.node.getName():
            
            if entry.getIntoNodePath().getParent().getName() == "EndOfLevel": #Plane entering Finish area
                    self.myImage.hide() #hide cursor image during death animation
                    self.beatLevel()
                    base.disableParticles() #disable physics when hit                   
                    self.engineSound.stop() #control volume
                    self.MusicSound.setVolume(0.5) #control volume
                    #Set Congratulations Message
                    print "CONGRATULATIONS"
                    self.msg.addMessage("FINAL DA FASE", 3)
                    #!!! PROGRAMAR AQUI !!!
                    #Set next level
                    #!!! PROGRAMAR AQUI !!!
                    #Player();
                    #Set final points
                    #!!! PROGRAMAR AQUI !!!
            else:                  
                    self.myImage.hide() #hide cursor image during death animation
                    self.explode()                 
                    base.disableParticles() #disable physics when hit                 
                    self.engineSound.stop() #control volume
                    self.MusicSound.setVolume(0.5) #control volume   
                    
    def evtFreeLookON(self): #Function for freelook on
        if self.landing == False:
            self.freeLook = True
            self.camRotH = 270
            self.camRotV = 80
            self.myImage.hide()      
    def evtFreeLookOFF(self): #Function for freelook off
        if self.landing == False:
            self.freeLook = False
            base.camera.setPos(0,-20,2)
            base.camera.lookAt(self.aimNode)
            self.myImage.show() 
    def __del__(self): #Function that delete features of the airplane
        self.ignoreAll()
        self.contrail.cleanup()
        
        #delete stop the sound
        self.Sound.stop()
        self.audio3d.detachSound(self.Sound)
        self.engineSound.stop()
        self.MusicSound.stop()
        
        base.camera.reparentTo(render)
        base.camera.setPos(2000,2000,800)
        base.camera.lookAt(0,0,0)
        if self.moveTask != 0:
            taskMgr.remove(self.moveTask)
        if self.mouseTask != 0:
            taskMgr.remove(self.mouseTask)        
        self.node.removeNode()
        #hide cursor image after death
        self.myImage.hide()
        messenger.send( 'player-death' ) 
    def evtSpeedUp(self): #Function that conrol event that increse speed
        if self.landing:
            return 0 
        self.speed += 5
        self.engineSound.setPlayRate(self.engineSound.getPlayRate()+0.05)
        if self.speed > self.speedMax:
            self.speed = self.speedMax
            #self.engineSound.setVolume(1)
            self.engineSound.setPlayRate(1.5)
        self.zoom = -5-(self.speed/10)
        #speed text
        #self.textSpeed.setText('Speed: '+str(self.speed))
    def evtSpeedDown(self): #Function that control event that decrease speed
        if self.landing:
            return 0
        #speed text
        #self.textSpeed.setText('Speed: '+str(self.speed))
        self.speed -= 5
        self.engineSound.setPlayRate(self.engineSound.getPlayRate()-0.05)
        if self.speed < 0:
            self.speed = 0
            #self.engineSound.setVolume(0)
            self.engineSound.setPlayRate(0.5)
        self.zoom = -5-(self.speed/10)
    def evtMenuOpen(self): #Function that control open menu event(ESC)
        taskMgr.remove(self.mouseTask)
        taskMgr.remove(self.moveTask)
        self.myImage.hide()
        props = WindowProperties()
        props.setCursorHidden(0)
        base.win.requestProperties(props)
        #disable physics when esc is pressed
        base.disableParticles()
        #control volume
        self.engineSound.stop()
        self.MusicSound.setVolume(0.5)
    def evtMenuClose(self): #Function that control close menu event(ESC)
        #self.addEvents()
        props = WindowProperties()
        props.setCursorHidden(1)
        base.win.requestProperties(props)
        self.mouseTask = taskMgr.add(self.mouseUpdateTask, 'mouse-task')
        self.moveTask = taskMgr.add(self.moveUpdateTask, 'move-task')
        self.myImage.show()
        #enable physics after menu closed
        base.enableParticles()
        #control volume
        self.engineSound.play()
        self.MusicSound.setVolume(1.5)
class Lixeira(DirectObject.DirectObject):#Class Lixeira for End of Level trigger
    #def __init__(self, start, orign):
    def __init__(self, start):
        self.node = NodePath('EndOfLevel')
       
        self.start = start
        #self.start = (1000,1000,200)
        self.collisionHandler = 0
        self.particleEffect = 0
        self.loadModel()
        self.addCollisions()
        self.setUpEvents()
    def loadModel(self): #Function that loads Lixeira
        self.node.reparentTo(render)
        self.node.setPos(self.start)
        self.nodeModel = loader.loadModel('lixeira')
        self.nodeModel.reparentTo(self.node)
        self.nodeModel.setScale(8)
        lixeiraTexture = loader.loadTexture("grade.jpg")
        self.nodeModel.setTexture(lixeiraTexture)
    def addCollisions(self): #Functions that add collisions for the duto
        self.collider = self.nodeModel.find("**/octree-root")
        self.collider.setName("EndOfLevel")
        self.collider.setCollideMask(BitMask32.allOn())
    def evtHit(self, entry): #Function that controls the event when the Lixeira hit something

         #if entry.getFromNodePath() == self.cNodePath and entry.getIntoNodePath().getName() != self.node.getTag("orign"):
        if entry:
            if entry.getIntoNodePath().getParent().getName() != self.node.getTag("orign"):
                if entry.getIntoNodePath().getParent().getTag('targetID') != "":
                    messenger.send( entry.getIntoNodePath().getParent().getTag('targetID')+'-evtGotHit')
                    
    def setUpEvents(self): #Function that set events that will be accepted
        self.accept('lixeiraHit'+str(id(self)), self.evtHit)

    def __del__(self): #Function that delete the Lixeira node
        self.node.removeNode()

class dutoAr(DirectObject.DirectObject):#Class Lixeira for End of Level trigger
    #def __init__(self, start, orign):
    def __init__(self, start):
        self.node = NodePath('increasePlayerUp')
        #self.node.setTag("orign",orign)
        self.start = start
        #self.start = (1000,1000,200)
        self.collisionHandler = 0
        self.particleEffect = 0
        self.loadModel()
        self.setUpEvents()
        self.addCollisions()
    def loadModel(self): #Function that loads Lixeira
        self.node.reparentTo(render)
        self.node.setPos(self.start)
        self.nodeModel = loader.loadModel('cubo')
        self.nodeModel.reparentTo(self.node)
        self.nodeModel.setScale(20)
        dutoArTexture = loader.loadTexture("textura_roxa.jpg")
        self.nodeModel.setTexture(dutoArTexture)
    def addCollisions(self): #Functions that add collisions for the duto
        self.cNode = CollisionNode('duto')
        self.cNode.addSolid(CollisionSphere(0,0,0,50))
        self.cNodePath = self.node.attachNewNode(self.cNode)
        self.cNodePath.show()
        #self.collisionHandler.addInPattern('hit')
        #base.cTrav.addCollider(self.cNodePath, self.collisionHandler)
        
    def evtHit(self, entry): #Function that controls the event when the Lixeira hit something
        #if entry.getFromNodePath() == self.cNodePath and entry.getIntoNodePath().getName() != self.node.getTag("orign"):
        if entry:
            if entry.getIntoNodePath().getParent().getName() != self.node.getTag("orign"):
                if entry.getIntoNodePath().getParent().getTag('targetID') != "":
                    messenger.send( entry.getIntoNodePath().getParent().getTag('targetID')+'-evtGotHit')
    
    def setUpEvents(self): #Function that set events that will be accepted
        self.accept('lixeiraHit'+str(id(self)), self.evtHit)
    def __del__(self): #Function that delete the Lixeira node
        self.node.removeNode()

class MessageManager(DirectObject.DirectObject): #Class that control messages 
    def __init__(self): #Class constructor
        # list of current messages
        self.messages =[]
        # start the erase task
        self.eraseTaskPointer = taskMgr.doMethodLater(1.0, self.__eraseTask, 'erase-task')
    def __eraseTask(self, task): #Function that erase messages
        i = 0
        for message in self.messages:
            message[1] -= 1
            if message[1] <= 0:
                message[0].destroy()
                del self.messages[i]
            i +=1

        return task.again     
    def addMessage(self, message, lifetime): #Function that add messages
        self.messages.append([ 
                             OnscreenText(text = message, pos = (0, (0.75-len(self.messages)*0.1)), 
                                           scale = 0.07, fg=(1,1,1,1), bg=(0.2,0.2,0.2,0.5)),
                             lifetime
                              ]) 
class StartMenu(DirectObject.DirectObject): #Class for main menu
    def __init__(self,cond=1): #Class constructor
        
        self.frame = DirectFrame(frameSize=(-0.5, 0.5, -0.5, 0.5), frameColor=(0.8,0.8,0.8,0), pos=(0,0,0))
        self.frame2 = DirectFrame(parent=render2d, image="media/TitleScreen.jpg", sortOrder=(-1))
        #self.frame['frameColor']=(0.8,0.8,0.8,0)

        #self.headline = DirectLabel(parent=self.frame, text="GAIVOTA", scale=0.085, frameColor=(0,0,0,0), pos=(0,0,0.3))
        
        self.startButton = DirectButton(parent=self.frame, text="Start Game", command=self.doStartGame, pos=(1,0,-0.5), text_scale=0.08, text_fg=(1,1,1,1), text_align=TextNode.ARight, borderWidth=(0.005,0.005), frameSize=(-0.25, 0.25, -0.03, 0.06), frameColor=(0.8,0.8,0.8,0)) 
        self.creditsButton = DirectButton(parent=self.frame, text="Credits", command=self.showCredits, pos=(1,0,-0.6), text_scale=0.08, text_fg=(1,1,1,1), text_align=TextNode.ARight, borderWidth=(0.005,0.005), frameSize=(-0.25, 0.25, -0.03, 0.06), frameColor=(0.8,0.8,0.8,0))
        self.quitButton = DirectButton(parent=self.frame, text="Quit", command=sys.exit, pos=(1,0,-0.7), text_scale=0.08, text_fg=(1,1,1,1), text_align=TextNode.ARight, borderWidth=(0.005,0.005), frameSize=(-0.25, 0.25, -0.03, 0.06), frameColor=(0.8,0.8,0.8,0))
        
        self.showMenu()
        self.credits = Credits()
        #Carrega Imagem do Inicio (TitleScreen)
        
        #b=OnscreenImage(parent=render2d, image="media/TitleScreen.jpg")
        #base.cam.node().getDisplayRegion(0).setSort(20)  
        
    def showMenu(self): #Function that show menu
        self.frame.show()
        self.frame2.show()
        # send an event for the player class
        messenger.send( "startMenuOpen" )    
    def hideMenu(self): #Function that hide menu
        self.frame.destroy()
        self.frame2.destroy()
        # send an event for the player class
        messenger.send( "startMenuClosed" )    
    def doStartGame(self): #Function that show graphic settings
        self.hideMenu()
        Game()     
    def showCredits(self): #Function that show credits
        self.credits.show()
class MainMenu(DirectObject.DirectObject):
    def __init__(self,cond=1): #Class constructor
        
        self.frame = DirectFrame(frameSize=(-0.3, 0.3, -0.4, 0.4))
        self.frame['frameColor']=(0.8,0.8,0.8,1)

        self.headline = DirectLabel(parent=self.frame, text="Main Menu", scale=0.085, frameColor=(0,0,0,0), pos=(0,0,0.3))
        
        self.graphicsButton = DirectButton(parent=self.frame, text="Graphics Settings", command=self.showGraphicsSettings, pos=(0,0,0.1), text_scale=0.06, borderWidth=(0.005,0.005), frameSize=(-0.25, 0.25, -0.03, 0.06)) 
        self.creditsButton = DirectButton(parent=self.frame, text="Credits", command=self.showCredits, pos=(0,0,0), text_scale=0.06, borderWidth=(0.005,0.005), frameSize=(-0.25, 0.25, -0.03, 0.06))
        self.quitButton = DirectButton(parent=self.frame, text="Quit", command=sys.exit, pos=(0,0,-0.1), text_scale=0.06, borderWidth=(0.005,0.005), frameSize=(-0.25, 0.25, -0.03, 0.06))
        self.backButton = DirectButton(parent=self.frame, text="Resume", command=self.hideMenu, pos=(0,0,-0.3), text_scale=0.06, borderWidth=(0.005,0.005), frameSize=(-0.25, 0.25, -0.03, 0.06))
        
        self.hideMenu()
        self.accept('escape', self.showMenu)
        
        self.graphicsSettings = GraphicsSettings()
        self.credits = Credits() 
    def showMenu(self): #Function that show menu
        self.frame.show()
        # send an event for the player class
        messenger.send( "menuOpen" )  
    def hideMenu(self): #Function that hide menu
        self.frame.hide()
        # send an event for the player class
        messenger.send( "menuClosed" )  
    def showGraphicsSettings(self): #Function that show graphic settings
        self.graphicsSettings.show()       
    def showCredits(self): #Function that show credits
        self.credits.show()
class GameOverMenu(DirectObject.DirectObject):
    def __init__(self,cond=1):#Class constructor
        
        self.frame = DirectFrame(frameSize=(-0.3, 0.3, -0.4, 0.4))
        self.frame['frameColor']=(0.8,0.8,0.8,1)

        self.headline = DirectLabel(parent=self.frame, text="GAME OVER", scale=0.085, frameColor=(0,0,0,0), pos=(0,0,0.3))
        
        self.retryButton = DirectButton(parent=self.frame, text="Retry", command=self.doRestart, pos=(0,0,0.1), text_scale=0.06, borderWidth=(0.005,0.005), frameSize=(-0.25, 0.25, -0.03, 0.06)) 
        #self.giveupButton = DirectButton(parent=self.frame, text="Give Up!", command=self.showEndingCredits, pos=(0,0,0), text_scale=0.06, borderWidth=(0.005,0.005), frameSize=(-0.25, 0.25, -0.03, 0.06))
        self.giveupButton = DirectButton(parent=self.frame, text="Give Up!", command=sys.exit, pos=(0,0,0), text_scale=0.06, borderWidth=(0.005,0.005), frameSize=(-0.25, 0.25, -0.03, 0.06))
        
        self.acceptOnce('escape', self.hideMenu)
        
        self.credits = Credits()   
    def showMenu(self): #Function that show menu
        self.frame.show()
        # send an event for the player class
        messenger.send( "menuOpen" )
    def hideMenu(self): #Function that hide menu
        self.frame.hide()
        # send an event for the player class
        messenger.send( "menuClosed" ) 
    def doRestart(self): #Function that show graphic settings
        self.hideMenu()
        props = WindowProperties()
        props.setCursorHidden(1)
        base.win.requestProperties(props)
        Player()     
    def showEndingCredits(self): #Function that show credits
        self.credits.show()
class Game(DirectObject.DirectObject): #Class that control game features - main class  
    def __init__(self): #Class constructor
        MainMenu()
        #PStatClient.connect()
        props = WindowProperties()
        props.setCursorHidden(1)
        base.win.requestProperties(props)
        #anti aliasing
        render.setAntialias(AntialiasAttrib.MAuto)
        base.camLens.setFar(5100)
        base.camLens.setFov(100)

        base.cTrav = CollisionTraverser('ctrav')
        base.cTrav.setRespectPrevTransform(True)
        base.enableParticles()
        
        self.environment = Environment()
        Player()
        self.msg = MessageManager()
        self.lvl = 1
        self.kills = 0
        self.shoots = 0
        
        self.accept('player-death', self.evtPlayerDeath)
        self.accept('mouse1',self.evtShoot)
        
        #Add game over sound
        self.gameOverSound = loader.loadSfx("smas44.mp3")
        self.gameOverSound.setVolume(4)
        self.gameOverSound.setPlayRate(1) 
    def evtPlayerDeath(self): #Function that controls the player's death
        self.msg.addMessage("Game Over", 6)
        #enable cursor after death
        props = WindowProperties()
        props.setCursorHidden(0)
        base.win.requestProperties(props)
        self.gameOverSound.play()
        GameOverMenu()      
    def evtShoot(self): #Function that control the player's shoot
        self.shoots +=1      
class GraphicsSettings(DirectObject.DirectObject): #Class for graphic settings  
    def __init__(self): #Class contructor
        #available resolutions and multisampling levels
        self.resolutions = ['800 600', '1024 768', '1152 864', '1280 720', '1280 960', '1440 900', '1680 1050', '1920 1080']
        self.multisampling = ["0", "2","4","8","16"]
        
        self.frame = DirectFrame(frameSize=(-0.5, 0.5, -0.5, 0.5), frameColor=(0.8,0.8,0.8,1), pos=(0,0,0))
        self.headline = DirectLabel(parent=self.frame, text="Graphics Settings", scale=0.085, frameColor=(0,0,0,0), pos=(0,0,0.4))
        
        
        self.resolutionText = DirectLabel(
                                          parent=self.frame, 
                                          text="Resolution", 
                                          scale=0.07, 
                                          frameColor=(0,0,0,0), 
                                          pos=(-0.4,0,0.3),
                                          text_align=TextNode.ALeft)
        
        self.resolutionMenu = DirectOptionMenu(parent=self.frame, scale=0.07,items=self.resolutions,
                                highlightColor=(0.65,0.65,0.65,1),textMayChange=1, pos=(0,0,0.3))
        
        self.aaText = DirectLabel(
                                          parent=self.frame, 
                                          text="Antialiasing", 
                                          scale=0.07, 
                                          frameColor=(0,0,0,0), 
                                          pos=(-0.4,0,0.2),
                                          text_align=TextNode.ALeft)
        
        self.aaMenu = DirectOptionMenu(parent=self.frame, scale=0.07,items=self.multisampling,
                                highlightColor=(0.65,0.65,0.65,1),textMayChange=1, pos=(0,0,0.2))
        
        self.fullscreenText = DirectLabel(
                                          parent=self.frame, 
                                          text="Fullscreen", 
                                          scale=0.07, 
                                          frameColor=(0,0,0,0), 
                                          pos=(-0.4,0,0.1),
                                          text_align=TextNode.ALeft)        
        self.fullscreenBox = DirectCheckButton(parent=self.frame, scale=.06, pos=(0.053,0,0.13))
        
        self.fpsText = DirectLabel(
                                          parent=self.frame, 
                                          text="Show FPS", 
                                          scale=0.07, 
                                          frameColor=(0,0,0,0), 
                                          pos=(-0.4,0,0.0),
                                          text_align=TextNode.ALeft)
        self.fpsBox = DirectCheckButton(parent=self.frame, scale=.06, pos=(0.053,0,0.03))

        self.noticeText = DirectLabel(
                                          parent=self.frame, 
                                          text="You need to restart the game to make these changes take effect.", 
                                          scale=0.04, 
                                          frameColor=(0,0,0,0), 
                                          pos=(0,0,-0.3),
                                          )
        self.saveButton = DirectButton(parent=self.frame, text="Save", command=self.saveConfig, pos=(-0.4,0,-0.4), scale=0.07)
        self.backButton = DirectButton(parent=self.frame, text="Back", command=self.hide, pos=(0.4,0,-0.4), scale=0.07)
        self.hide()
        self.loadConfig()    
    def loadConfig(self): #Function that load configuration
        self.resolutionMenu.set( self.resolutions.index( ConfigVariableString('win-size').getValue() ) )
        
        self.aaMenu.set( self.multisampling.index( str(ConfigVariableInt('multisamples').getValue()) ) )
        
        if ConfigVariableString('show-frame-rate-meter').getValue() == "#t":
            self.fpsBox["indicatorValue"] = True
            self.fpsBox.setIndicatorValue()
        else:
            self.fpsBox["indicatorValue"] = False
            self.fpsBox.setIndicatorValue()
        
            
        if ConfigVariableBool('fullscreen').getValue() == True:
            self.fullscreenBox["indicatorValue"] = True
            self.fullscreenBox.setIndicatorValue()
        else:
            self.fullscreenBox["indicatorValue"] = False
            self.fullscreenBox.setIndicatorValue()    
    def saveConfig(self): #Function that save configuration
        cfgFile = open('cfg.prc', 'w')
        cfgFile.write("model-path $MAIN_DIR/media/n")

        cfgFile.write("win-size "+self.resolutionMenu.get()+"\n")
        cfgFile.write("multisamples "+self.aaMenu.get()+"\n")
        
        if self.fullscreenBox["indicatorValue"]:
            cfgFile.write("fullscreen #t\n")
        else:
            cfgFile.write("fullscreen #f\n")            
        
        if self.fpsBox["indicatorValue"]:
            cfgFile.write("show-frame-rate-meter #t\n")
        else:
            cfgFile.write("show-frame-rate-meter #f\n")
        
        cfgFile.close()
    def show(self): #Function that display window
        self.frame.show()         
    def hide(self): #Function that hide window
        self.frame.hide()    
class Credits(DirectObject.DirectObject):  
    def __init__(self): #Class constructor
        self.frame = DirectFrame(frameSize=(-0.5, 0.5, -0.5, 0.5), frameColor=(0.8,0.8,0.8,1), pos=(0,0,0))
        self.headline = DirectLabel(parent=self.frame, text="Credits", scale=0.085, frameColor=(0,0,0,0), pos=(0,0,0.4))
        
        self.Text = DirectLabel(
                                      parent=self.frame, 
                                      text="GAIVOTA\n\nJogo criado para COS600 - Animacao e Jogos\nEngenharia de Computacao e Informacao (ECI)\nUniversidade Federal do Rio de Janeiro (UFRJ) | Brazil\nMarch ~ July/2010\n\nAuthors: \nFilipe Yamamoto, \nFabio Castanheira, \nMiguel Fernandes\n\nCheck out our site to see project details\nhttp://code.google.com/p/gaivota/\n\nVersion: 0.057 (Pre-Alpha)\n\nBased on Akuryou's Flight game", 
                                      scale=0.04, 
                                      frameColor=(0,0,0,0), 
                                      pos=(-0.48,0,0.35),
                                      text_align=TextNode.ALeft)
        
        self.backButton = DirectButton(parent=self.frame, text="back", command=self.hide, pos=(0,0,-0.4), scale=0.07)
        self.hide()   
    def show(self): #Function that display the window
        self.frame.show()
    def hide(self): #Function that hide the window
        self.frame.hide()
StartMenu()
run()
