import global_variables
import cv2
import numpy as np
from PIL import Image as im
import imutils


def generate_masks_otsu(image, f_name, splitimage):
    """
    > The function takes as input the path of the image and the path of the output directory. It returns
    the mask of the image
    
    :param path_image_query2: path to the image to be processed
    :param dir_output: the directory where the output images will be saved
    :param threshold_value: The value that the pixels will be compared to, defaults to 100 (optional)
    :return: the mask of the image.
    """

    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
    kernel = np.ones((2,2),np.uint8)
    image_e= cv2.erode(image_gray,kernel,iterations = 2)
    a,imgt = cv2.threshold(image_e, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
    # Apply close morphology operator in order denoise
    size = 5
    element = cv2.getStructuringElement(cv2.MORPH_RECT, (2*size+1, 2*size+1))
    mask_close = cv2.morphologyEx(imgt, cv2.MORPH_CLOSE, element, iterations=5)
                        
    # Save the image in dir_results
    cv2.imwrite(f'{global_variables.dir_results}{f_name}.png', mask_close)
            
    return

def generate_masks(image, f_name, mayhave_split): #NOVA FUNCIO PER DETECTAR ELS QUADRES fent el LAPLACIA
    """
    > The function takes as input the path of the image and the path of the output directory. It returns
    the mask of the image
    
    :param path_image_query2: path to the image to be processed
    :param dir_output: the directory where the output images will be saved
    :param threshold_value: The value that the pixels will be compared to, defaults to 100 (optional)
    :return: the mask of the image.
    """


    #Parametres provats en el seguent ordre: thr per la binaritzacio del laplacia, size opening 1, size dilation, size opening 2
    # Funcionen bastant semblant 7,3,5,20  / 10,2,5,20 / 10,2,3,20 (igual millor la tercera opcio)
    # No van be: 10,2,7,20 / 10,2,7,25 / 10,3,5,20 /  10,2,5,25

    image_cpy = image.copy()
    height,width,channels = image.shape
  

    # remove noise
    image_blur = cv2.GaussianBlur(image,(7,7),0)

    gray_image = cv2.cvtColor(image_blur, cv2.COLOR_BGR2GRAY) 

    # convolute with proper kernels
    lap = cv2.Laplacian(gray_image,cv2.CV_32F, ksize = 3)

    th, laplacian = cv2.threshold(lap, 10,255,cv2.THRESH_BINARY)

    """cv2.namedWindow("lap", cv2.WINDOW_NORMAL)
    cv2.imshow("lap", laplacian)
    cv2.waitKey(0)
    cv2.destroyAllWindows()"""

    # Apply morphology 
  
    element = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask_close = cv2.morphologyEx(laplacian, cv2.MORPH_OPEN, element)

    element_dil = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
    dilation = cv2.dilate(mask_close,element_dil)

    """cv2.namedWindow("lap", cv2.WINDOW_NORMAL)
    cv2.imshow("lap", mask_close)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    cv2.namedWindow("lap", cv2.WINDOW_NORMAL)
    cv2.imshow("lap", dilation)
    cv2.waitKey(0)
    cv2.destroyAllWindows()"""

      
    element = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask_close_dil = cv2.morphologyEx(dilation, cv2.MORPH_OPEN, element)

    """cv2.namedWindow("lap", cv2.WINDOW_NORMAL)
    cv2.imshow("lap", mask_close_dil)
    cv2.waitKey(0)
    cv2.destroyAllWindows()"""

    element2 = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    mask_open2 = cv2.morphologyEx(mask_close_dil, cv2.MORPH_CLOSE, element2)
    """cv2.namedWindow("lap", cv2.WINDOW_NORMAL)
    cv2.imshow("lap", mask_open2)
    cv2.waitKey(0)
    cv2.destroyAllWindows()"""


    contours, hierarchy = cv2.findContours(np.uint8(mask_open2), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    """parent_contours = []
    hierarchy = hierarchy[0] # get the actual inner list of hierarchy descriptions

    # For each contour find if it is parent
    for component in zip(contours, hierarchy):
        currentContour = component[0]
        currentHierarchy = component[1]       
        if currentHierarchy[3] < 0:
            # these are the outermost parent components
            parent_contours.append(currentContour)"""


    areaArray = []
    for i, c in enumerate(contours):
        x_c,y_c,w_c,h_c = cv2.boundingRect(c)
        #area = cv2.contourArea(c)
        areaArray.append(w_c*h_c)




    #first sort the array by area
    sorteddata = sorted(zip(areaArray, contours), key=lambda x: x[0], reverse=True)

    #find the nth largest contours
  
    firstgestcontour = sorteddata[0][1]
    rect = cv2.minAreaRect(firstgestcontour) # this is a 2D box that has (center(x, y), (width, height), angle of rotation) 
    box1 = cv2.boxPoints(rect) #obtain the 4 corners to draw the rectangle
    box1 = np.int0(box1)
    cv2.drawContours(image_cpy,[box1],0,(0,0,255),2)
    center1 = rect[0]
    angle1 = rect[2]
    
    #filling external parts with black
    (x, y, w, h) = cv2.boundingRect(firstgestcontour)
    painting1 = image_cpy[y:y + h, x:x + w]

    rotated = imutils.rotate_bound(painting1, -angle1) 
    cv2.imshow("Rotated (Correct)", rotated) # faltaria crear la mask de lo que no ens interessa un cop rotat
   
  
    # 4 points of the corners (starting from the corner with highest y (THE 0,0 is in the top left ) (if two have the same highest y, then the rightmost point) rotating clockwise). [1,2,3,0]
    print(box1)
    print("angle = "+str(rect[2]))


    num_paintings = 1
    if len(contours) > 1 and mayhave_split:
        
        secondlargestcontour = sorteddata[1][1]
        rect = cv2.minAreaRect(secondlargestcontour)
        box2 = cv2.boxPoints(rect)
        box2 = np.int0(box2)
        h2= rect[1][1]
        w2= rect[1][0]
        center2 = rect[0]
        angle2 = rect[2]
        print("angle = "+str(angle2))
     


        if( h2+w2 > 0.06*(width+height) and h2+w2 < 0.95*(width+height) ) and (h2/w2 < 7 and w2/h2 < 7):
        
            cv2.drawContours(image_cpy,[box2],0,(0,255,0),2)
            num_paintings = 2
              
        

        if len(contours) > 2:
            thirdlargestcontour = sorteddata[2][1]
            rect = cv2.minAreaRect(thirdlargestcontour)
            box3 = cv2.boxPoints(rect)
            box3 = np.int0(box3)
            h3= rect[1][1]
            w3= rect[1][0]
            center3 = rect[0]
            angle3 = rect[2]
            print("angle = "+str(angle3))

 
            if( h3+w3 > 0.06*(width+height) and h3+w3 < 0.95*(width+height) ) and (h3/w3 < 7 and w3/h3 < 7) :
                cv2.drawContours(image_cpy,[box3],0,(255,0,0),2)
                num_paintings = 3



    cv2.namedWindow("lap", cv2.WINDOW_NORMAL)
    cv2.imshow("lap", image_cpy)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_laplacian.png', laplacian)
    #cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_laplacian_open.png', np.uint8(mask_open))
    #cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_laplaian_open_dilate.png', np.uint8(dilation))
    cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_laplaian_open_dilate_open.png', np.uint8(mask_open2))
    cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_split_laplacian_boxes.png', image_cpy)


    #FALTA FILTRAR QUE NO ESTIGUIN UNS A DINS DELS ALTRES I ORDENAR ELS QUADRES --> ho faria amb el centre que tenim de cada un
    painting_box = []
    return num_paintings, painting_box



 