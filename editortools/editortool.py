from OpenGL import GL
import numpy
from depths import DepthOffset
from pymclevel import BoundingBox

class EditorTool(object):
    surfaceBuild = False
    panel = None
    optionsPanel = None
    toolIconName = None
    worldTooltipText = None
    previewRenderer = None

    tooltipText = "???"

    def levelChanged(self):
        """ called after a level change """
        pass

    @property
    def statusText(self):
        return ""

    @property
    def cameraDistance(self):
        return self.editor.cameraToolDistance

    def toolEnabled(self):
        return True

    def __init__(self, editor):
        self.editor = editor

    def toolReselected(self):
        pass

    def toolSelected(self):
        pass

    def drawTerrainReticle(self):
        pass

    def drawTerrainMarkers(self):
        pass

    def drawTerrainPreview(self, origin):
        if self.previewRenderer is None:
            return
        self.previewRenderer.origin = map(lambda a, b: a - b, origin, self.level.bounds.origin)

        GL.glPolygonOffset(DepthOffset.ClonePreview, DepthOffset.ClonePreview)
        GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
        self.previewRenderer.draw()
        GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)

    def rotate(self, amount=1):
        pass

    def roll(self, amount=1):
        pass

    def flip(self, amount=1):
        pass

    def mirror(self, amount=1):
        pass

    def swap(self, amount=1):
        pass

    def mouseDown(self, evt, pos, direction):
        '''pos is the coordinates of the block under the cursor,
        direction indicates which face is under it.  the tool performs
        its action on the specified block'''

        pass

    def mouseUp(self, evt, pos, direction):
        pass

    def mouseDrag(self, evt, pos, direction):
        pass

    def increaseToolReach(self):
        "Return True if the tool handles its own reach"
        return False

    def decreaseToolReach(self):
        "Return True if the tool handles its own reach"
        return False

    def resetToolReach(self):
        "Return True if the tool handles its own reach"
        return False

    def confirm(self):
        ''' called when user presses enter '''
        pass

    def cancel(self):
        '''cancel the current operation.  called when a different tool
        is picked, escape is pressed, or etc etc'''
        self.hidePanel()

    #        pass

    def findBestTrackingPlane(self, face):
        cv = list(self.editor.mainViewport.cameraVector)
        cv[face >> 1] = 0
        cv = map(abs, cv)

        return cv.index(max(cv))

    def drawToolReticle(self):

        '''get self.editor.blockFaceUnderCursor for pos and direction.
        pos is the coordinates of the block under the cursor,
        direction indicates which face is under it. draw something to
        let the user know where the tool is going to act.  e.g. a
        transparent block for the block placing tool.'''

        pass

    def drawToolMarkers(self):
        ''' draw any markers the tool wants to leave in the field
        while another tool is out.  e.g. the current selection for
        SelectionTool'''

        pass

    def selectionChanged(self):
        """ called when the selection changes due to nudge. other tools can be active. """
        pass

    edge_factor = 0.1

    def boxFaceUnderCursor(self, box):
        if self.editor.mainViewport.mouseMovesCamera:
            return None, None

        p0 = self.editor.mainViewport.cameraPosition
        normal = self.editor.mainViewport.mouseVector
        if normal is None:
            return None, None

        points = {}

#        glPointSize(5.0)
#        glColor(1.0, 1.0, 0.0, 1.0)
#        glBegin(GL_POINTS)

        for dim in range(3):
            dim1 = dim + 1
            dim2 = dim + 2
            dim1 %= 3
            dim2 %= 3

            def pointInBounds(point, x):
                return box.origin[x] <= point[x] <= box.maximum[x]

            neg = normal[dim] < 0

            for side in 0, 1:

                d = (box.maximum, box.origin)[side][dim] - p0[dim]

                if d >= 0 or (neg and d <= 0):
                    if normal[dim]:
                        scale = d / normal[dim]

                        point = map(lambda a, p: (a * scale + p), normal, p0)
    #                    glVertex3f(*point)

                        if pointInBounds(point, dim1) and pointInBounds(point, dim2):
                            points[dim * 2 + side] = point

#        glEnd()

        if not len(points):
            return None, None

        cp = self.editor.mainViewport.cameraPosition
        distances = dict((numpy.sum(map(lambda a, b: (b - a) ** 2, cp, point)), (face, point)) for face, point in points.iteritems())
        if not len(distances):
            return None, None

        # When holding alt, pick the face opposite the camera
        # if key.get_mods() & KMOD_ALT:
        #    minmax = max
        # else:

        face, point = distances[min(distances.iterkeys())]

        # if the point is near the edge of the face, and the edge is facing away,
        # return the away-facing face

        dim = face // 2
        side = face & 1

        dim1, dim2 = dim + 1, dim + 2
        dim1, dim2 = dim1 % 3, dim2 % 3
        cv = self.editor.mainViewport.cameraVector

        # determine if a click was within self.edge_factor of the edge of a selection box side. if so, click through
        # to the opposite side
        for d in dim1, dim2:
            edge_width = box.size[d] * self.edge_factor
            facenormal = [0, 0, 0]
            cameraBehind = False

            if point[d] - box.origin[d] < edge_width:
                facenormal[d] = -1
                cameraBehind = cp[d] - box.origin[d] > 0
            if point[d] - box.maximum[d] > -edge_width:
                facenormal[d] = 1
                cameraBehind = cp[d] - box.maximum[d] < 0

            if numpy.dot(facenormal, cv) > 0 or cameraBehind:
                # the face adjacent to the clicked edge faces away from the cam
                return distances[max(distances.iterkeys())]

        return face, point

    def selectionCorners(self):
        """ returns the positions of the two selection corners as a pair of 3-tuples, each ordered x,y,z """

        if(None != self.editor.selectionTool.bottomLeftPoint and
           None != self.editor.selectionTool.topRightPoint):

            return (self.editor.selectionTool.bottomLeftPoint,
                    self.editor.selectionTool.topRightPoint)

        return None

    def selectionBoxForCorners(self, p1, p2):
        ''' considers p1,p2 as the marked corners of a selection.
        returns a BoundingBox containing all the blocks within.'''

        if self.editor.level is None:
            return None

        p1, p2 = list(p1), list(p2)
        # d = [(a-b) for a,b in zip(p1,p2)]
        for i in range(3):
            if p1[i] > p2[i]:
                t = p2[i]
                p2[i] = p1[i]
                p1[i] = t

            p2[i] += 1

        size = map(lambda a, b: a - b, p2, p1)

        if p1[1] < 0:
            size[1] += p1[1]
            p1[1] = 0

        h = self.editor.level.Height
        if p1[1] >= h:
            p1[1] = h - 1
            size[1] = 1

        if p1[1] + size[1] >= h:
            size[1] = h - p1[1]

        return BoundingBox(p1, size)

    def selectionBox(self):
        ''' selection corners, ordered, with the greater point moved up one block for use as the ending value of an array slice '''
        c = self.selectionCorners()
        if c:
            return self.selectionBoxForCorners(*c)

        return None

    def selectionSize(self):
        ''' returns a tuple containing the size of the selection (x,y,z)'''
        c = self.selectionBox()
        if c is None:
            return None
        return c.size

    @property
    def maxBlocks(self):
        from leveleditor import Settings
        return Settings.blockBuffer.get() / 2  # assume block buffer in bytes

    def showPanel(self):
        pass

    def hidePanel(self):
        if self.panel and self.panel.parent:
            self.panel.parent.remove(self.panel)
            self.panel = None

