import global_variables
import cv2
import numpy as np
from PIL import Image as im





def generate_masks_ROT(image, f_name, mayhave_split, rotation_mask): 
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
    mask = np.zeros((height,width,3), dtype=np.uint8)

    # Remove noise
    image_blur = cv2.GaussianBlur(image,(9,9),0) # ! 9x9 to deal with the background filling at rotation
    gray_image = cv2.cvtColor(image_blur, cv2.COLOR_BGR2GRAY) 
    # Convolute with proper kernels
    lap = cv2.Laplacian(gray_image,cv2.CV_32F, ksize = 3)
    th, laplacian = cv2.threshold(lap, 9,255,cv2.THRESH_BINARY)

    # Check if rotation_mask is an array (if it is, it means that the image has been rotated and we need to apply the mask (an image/array))
    if isinstance(rotation_mask, np.ndarray):
        element_dil = cv2.getStructuringElement(cv2.MORPH_RECT, (15,15))
        rotation_mask_dil = cv2.dilate(rotation_mask, element_dil)
        # Remove the former transparent pixels (added at rotation)
        laplacian[rotation_mask_dil == 255] = 0   

    # Apply morphology 
    element = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask_close = cv2.morphologyEx(laplacian, cv2.MORPH_OPEN, element)

    element_dil = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
    dilation = cv2.dilate(mask_close,element_dil)
      
    element = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask_close_dil = cv2.morphologyEx(dilation, cv2.MORPH_OPEN, element)

    element2 = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
    mask_open2 = cv2.morphologyEx(mask_close_dil, cv2.MORPH_CLOSE, element2)

    contours, hierarchy = cv2.findContours(np.uint8(mask_open2), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    areaArray = []
    for i, c in enumerate(contours):
        x_c,y_c,w_c,h_c = cv2.boundingRect(c)
        #area = cv2.contourArea(c)
        areaArray.append(w_c*h_c)

    #first sort the array by area
    sorteddata = sorted(zip(areaArray, contours), key=lambda x: x[0], reverse=True)

    coordinates = []
    dist_to_image = []
    num_paintings = 0
    intersection_matrix = np.zeros((height,width))
    for i in range(len(sorteddata)):
        contour_matrix = np.zeros((height,width))

        contour = sorteddata[i][1]
        x, y, w, h = cv2.boundingRect(contour)
        
        if( h+w > 0.06*(width+height) and h+w < 0.96*(width+height) ) and h*w > 0.05*(width*height) and (h/w < 7 and w/h < 7):
            cv2.fillPoly(contour_matrix,pts=[np.array( [ [x,y], [x,y+h], [x+w, y+h], [x+w,y] ] )],color=255)
            logical_matrix = np.logical_and(contour_matrix,intersection_matrix)
            
            if np.all(logical_matrix == False):
                coordinates.append([x, y, x+w, y+h])
                dist_to_image.append(np.linalg.norm(np.asarray([0,0])-np.asarray([x+w/2,y+h/2])))
                num_paintings+=1
                mark_green_rectangle = cv2.rectangle(image_cpy, (x, y), (x + w, y + h), (0, 255,0 ), 3)
                cv2.fillPoly(intersection_matrix,pts=[np.array( [ [x,y], [x,y+h], [x+w, y+h], [x+w,y] ] )],color=255)
                cv2.fillPoly(mask,pts=[np.array( [ [x,y], [x,y+h], [x+w, y+h], [x+w,y] ] )],color=(255, 255,255 ))
        #if(num_paintings == 3):
            #break
    
    # Merge the masks of the paintings that are too close to each other
    for i in range(len(coordinates)):
        for j in range(len(coordinates)):
            if i != j:
                x1,y1,x2,y2 = coordinates[i]
                x3,y3,x4,y4 = coordinates[j]
                min_y_i = min(y1,y2)
                max_y_i = max(y1,y2)
                min_y_j = min(y3,y4)
                max_y_j = max(y3,y4)
                # If they have simillar widths and the distance between them is less than 0.5 of the width of the image
                if (abs(x2-x1) - abs(x4-x3) < 0.1*(x2-x1) ) and (abs(min_y_i-max_y_j) < height * 0.05 or abs(max_y_i-min_y_j) < height * 0.05):
                    # Merge the two paintings
                    x1 = min(x1,x3)
                    x2 = max(x2,x4)
                    y1 = min(y1,y3)
                    y2 = max(y2,y4)
                    coordinates[i] = [x1,y1,x2,y2]
                    coordinates[j] = [0,0,0,0]
                    num_paintings-=1
                    dist_to_image[i] = np.linalg.norm(np.asarray([0,0])-np.asarray([x2/2,y2/2]))
                    dist_to_image[j] = 1000000
                    cv2.fillPoly(mask,pts=[np.array( [ [x1,y1], [x1,y2], [x2, y2], [x2,y1] ] )],color=(255, 255,255 ))
                    cv2.fillPoly(intersection_matrix,pts=[np.array( [ [x1,y1], [x1,y2], [x2, y2], [x2,y1] ] )],color=255)
                    break
    
    # Remove the coordinates and distances of the paintings that were merged
    coordinates = [x for x in coordinates if x != [0,0,0,0]]
    dist_to_image = [x for x in dist_to_image if x != 1000000]

    sorted_coords = [x for _,x in sorted(zip(dist_to_image,coordinates))]
    cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_rot.png', image)
    cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_laplacian.png', laplacian)
    cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_laplacianblur.png', gray_image)
    cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_mask.png', np.uint8(mask))
    #cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_laplacian_open.png', np.uint8(mask_open))
    #cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_laplaian_open_dilate.png', np.uint8(dilation))
    cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_laplaian_open_dilate_open.png', np.uint8(mask_open2))
    cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_split_laplacian_boxes.png', image_cpy)

    return num_paintings, sorted_coords

def generate_masks_ROT2(image, f_name, mayhave_split): 
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
    green_channel = image[:,:,1]
    blue_channel = image[:,:,0]
    red_channel = image[:,:,2]
    not_fade_g = np.zeros([height,width])
    not_fade_r = np.zeros([height,width])
    not_fade_b = np.zeros([height,width])

    not_fade_r[red_channel == 0] = 1
    not_fade_b[blue_channel == 0] = 1
    not_fade_g[green_channel == 255] = 1
    fade = np.multiply(not_fade_g,not_fade_b, not_fade_r)

    element_dil = cv2.getStructuringElement(cv2.MORPH_RECT, (15,15))
    fadedilated = cv2.dilate(fade,element_dil)
    
    # remove noise
    image_blur = cv2.GaussianBlur(image,(9,9),0) # ! 9x9 to deal with the background filling at rotation

    gray_image = cv2.cvtColor(image_blur, cv2.COLOR_BGR2GRAY) 

    # Convolute with proper kernels
    canny = cv2.Canny(gray_image,10,70,apertureSize=3)

    #remove filled green pixels (added for the rotation)
    canny[fadedilated == 1] = 0   
    cv2.namedWindow("Canny", cv2.WINDOW_NORMAL)
    cv2.imshow("Canny", canny)
    cv2.waitKey(0)
    
    # Apply morphology 
    element_dil = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    dilation = cv2.dilate(canny,element_dil)
  
    element = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    mask_open = cv2.morphologyEx(dilation, cv2.MORPH_OPEN, element)

    # cv2.namedWindow("lap", cv2.WINDOW_NORMAL)
    # cv2.imshow("lap", dilation)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    # cv2.namedWindow("lap", cv2.WINDOW_NORMAL)
    # cv2.imshow("lap", mask_open)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    element2 = cv2.getStructuringElement(cv2.MORPH_RECT, (int(width*0.5),(int(width*0.5))))
    mask_close2 = cv2.morphologyEx(mask_open, cv2.MORPH_CLOSE, element)

    cv2.namedWindow("lap", cv2.WINDOW_NORMAL)
    cv2.imshow("lap", mask_close2)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    contours, hierarchy = cv2.findContours(np.uint8(mask_close2), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)


    areaArray = []
    for i, c in enumerate(contours):
        x_c,y_c,w_c,h_c = cv2.boundingRect(c)
        #area = cv2.contourArea(c)
        areaArray.append(w_c*h_c)


    #first sort the array by area
    sorteddata = sorted(zip(areaArray, contours), key=lambda x: x[0], reverse=True)


    coordinates = []
    dist_to_image = []
    num_paintings = 0
    intersection_matrix = np.zeros((height,width))
    for i in range(len(sorteddata)):
        contour_matrix = np.zeros((height,width))

        contour = sorteddata[i][1]
        x, y, w, h = cv2.boundingRect(contour)
        if( h+w > 0.06*(width+height) and h+w < 0.96*(width+height) ) and h*w > 0.05*(width*height) and (h/w < 7 and w/h < 7):
            cv2.fillPoly(contour_matrix,pts=[np.array( [ [x,y], [x,y+h], [x+w, y+h], [x+w,y] ] )],color=255)
            logical_matrix = np.logical_and(contour_matrix,intersection_matrix)
            
            if np.all(logical_matrix == False):
                coordinates.append([x, y, x+w, y+h])
                dist_to_image.append(np.linalg.norm(np.asarray([0,0])-np.asarray([x+w/2,y+h/2])))
                num_paintings+=1
                mark_red_rectangle = cv2.rectangle(image_cpy, (x, y), (x + w, y + h), (0, 0, 255), 3)
                cv2.fillPoly(intersection_matrix,pts=[np.array( [ [x,y], [x,y+h], [x+w, y+h], [x+w,y] ] )],color=255)
        if(num_paintings == 3):
            break

    sorted_coords = [x for _,x in sorted(zip(dist_to_image,coordinates))]
    # print(sorted_coords)

    cv2.namedWindow("lap", cv2.WINDOW_NORMAL)
    cv2.imshow("lap", image_cpy)
    cv2.waitKey(0)

    cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_laplacian.png', canny)
    #cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_laplacian_open.png', np.uint8(mask_open))
    #cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_laplaian_open_dilate.png', np.uint8(dilation))
    #cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_laplaian_open_dilate_open.png', np.uint8(mask_open))
    cv2.imwrite(global_variables.dir_query + global_variables.dir_query_aux + f_name + '_split_laplacian_boxes.png', image_cpy)



    return num_paintings, sorted_coords



 