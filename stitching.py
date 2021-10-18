import numpy as np
from scipy.ndimage.filters import convolve
from scipy.spatial.distance import cdist
from skimage import filters

from utils import pad


def harris_corners(img, window_size=3, k=0.04):
    """
    Compute Harris corner response map. Follow the math equation
    R=Det(M)-k(Trace(M)^2).

    Hint:
        You may use the function scipy.ndimage.filters.convolve for convolution, 
        which is already imported above
        
    Args:
        img: Grayscale image of shape (H, W)
        window_size: size of the window function
        k: sensitivity parameter

    Returns:
        response: Harris response image of shape (H, W)
    """

    H, W = img.shape
    window = np.ones((window_size, window_size))

    response = np.zeros((H, W))

    # step 1 in Harris corner detection: compute image derivatives
    dx = filters.sobel_v(img)
    dy = filters.sobel_h(img)

    #####################################
    #       START YOUR CODE HERE        #
    #####################################
    # step-2
    dx_q = dx ** 2
    dy_q = dy ** 2
    dxy = dx * dy
    # step-3
    dx_q_conv = convolve(dx_q, window, mode='constant')
    dy_q_conv = convolve(dy_q, window, mode='constant')
    dxy_conv = convolve(dxy, window, mode='constant')
    # step-4
    M = np.stack([dx_q_conv, dxy_conv, dxy_conv, dy_q_conv], axis=-1)
    response = dx_q_conv * dy_q_conv - dxy_conv ** 2 - k * (dx_q_conv + dy_q_conv) ** 2
    ######################################
    #        END OF YOUR CODE            #
    ######################################

    return response


def simple_descriptor(patch):
    """
    Describe the patch by normalizing the image values into a standard 
    normal distribution (having mean of 0 and standard deviation of 1) 
    and then flattening into a 1D array. 
    
    The normalization will make the descriptor more robust to change 
    in lighting condition.
    
    Hint:
        If a denominator is zero, divide by 1 instead.
    
    Args:
        patch: grayscale image patch of shape (h, w)
    
    Returns:
        feature: 1D array of shape (h * w)
    """
    feature = []

    #####################################
    #       START YOUR CODE HERE        #
    #####################################
    avg = np.mean(patch)
    std = np.std(patch)
    try:
        feature = (patch - avg) / std
    except ZeroDivisionError:
        feature = (patch - avg) / 1.0
    feature = feature.flatten()
    ######################################
    #        END OF YOUR CODE            #
    ######################################
    return feature


def describe_keypoints(image, keypoints, desc_func, patch_size=16):
    """
    Args:
        image: grayscale image of shape (H, W)
        keypoints: 2D array containing a keypoint (y, x) in each row
        desc_func: function that takes in an image patch and outputs
            a 1D feature vector describing the patch
        patch_size: size of a square patch at each keypoint
                
    Returns:
        desc: array of features describing the keypoints
    """

    image.astype(np.float32)
    desc = []

    for i, kp in enumerate(keypoints):
        y, x = kp
        patch = image[y - (patch_size // 2):y + ((patch_size + 1) // 2),
                x - (patch_size // 2):x + ((patch_size + 1) // 2)]
        desc.append(desc_func(patch))
    return np.array(desc)


def match_descriptors(desc1, desc2, threshold=0.5):
    """
    Match the feature descriptors by finding distances between them. A match is formed 
    when the distance to the closest vector is much smaller than the distance to the 
    second-closest, that is, the ratio of the distances should be smaller
    than the threshold. Return the matches as pairs of vector indices.
    
    Args:
        desc1: an array of shape (M, P) holding descriptors of size P about M keypoints
        desc2: an array of shape (N, P) holding descriptors of size P about N keypoints
        
    Returns:
        matches: an array of shape (Q, 2) where each row holds the indices of one pair 
        of matching descriptors
    """
    matches = []

    N = desc1.shape[0]
    dists = cdist(desc1, desc2)

    #####################################
    #       START YOUR CODE HERE        #
    #####################################
    idx_sort = np.argsort(dists, axis=-1)
    idx_valid = (dists[range(N), idx_sort[:, 1]] - dists[range(N), idx_sort[:, 0]]) > threshold
    matches = np.c_[np.arange(N), idx_sort[:, 0]]
    matches = matches[idx_valid]
    ######################################
    #        END OF YOUR CODE            #
    ######################################

    return matches


def fit_affine_matrix(p1, p2):
    """ Fit affine matrix such that p2 * H = p1 
    
    Hint:
        You can use np.linalg.lstsq function to solve the problem. 
        
    Args:
        p1: an array of shape (M, P)
        p2: an array of shape (M, P)
        
    Return:
        H: a matrix of shape (P * P) that transform p2 to p1.
    """

    assert (p1.shape[0] == p2.shape[0]), \
        'Different number of points in p1 and p2'
    p1 = pad(p1)
    p2 = pad(p2)

    #####################################
    #       START YOUR CODE HERE        #
    #####################################

    H = np.linalg.lstsq(p2, p1, rcond=None)[0]

    ######################################
    #        END OF YOUR CODE            #
    ######################################

    # Sometimes numerical issues cause least-squares to produce the last
    # column which is not exactly [0, 0, 1]
    H[:, 2] = np.array([0, 0, 1])
    return H


def ransac(keypoints1, keypoints2, matches, n_iters=200, threshold=20):
    """
    Use RANSAC to find a robust affine transformation

        1. Select random set of matches
        2. Compute affine transformation matrix
        3. Compute inliers
        4. Keep the largest set of inliers
        5. Re-compute least-squares estimate on all of the inliers

    Args:
        keypoints1: M1 x 2 matrix, each row is a point
        keypoints2: M2 x 2 matrix, each row is a point
        matches: N x 2 matrix, each row represents a match
            [index of keypoint1, index of keypoint 2]
        n_iters: the number of iterations RANSAC will run
        threshold: the number of threshold to find inliers

    Returns:
        H: a robust estimation of affine transformation from keypoints2 to
        keypoints 1
    """
    N = matches.shape[0]
    n_samples = int(N * 0.2)

    matched1 = pad(keypoints1[matches[:, 0]])
    matched2 = pad(keypoints2[matches[:, 1]])

    max_inliers = np.zeros(N)
    n_inliers = 0

    # RANSAC iteration start

    #####################################
    #       START YOUR CODE HERE        #
    #####################################
    for i in range(n_iters):
        index = np.random.choice(N, n_samples, replace=False)
        p1 = matched1[index]
        p2 = matched2[index]
        H = np.linalg.lstsq(p2, p1, rcond=None)[0]
        H[:, 2] = np.array([0, 0, 1])
        temp_max = np.linalg.norm(matched2.dot(H) - matched1, axis=1) ** 2 < threshold
        temp_n = np.sum(temp_max)
        if temp_n > n_inliers:
            max_inliers = temp_max.copy()
            n_inliers = temp_n
    H = np.linalg.lstsq(matched2[max_inliers],
                        matched1[max_inliers], rcond=None)[0]
    H[:, 2] = np.array([0, 0, 1])
    ######################################
    #        END OF YOUR CODE            #
    ######################################
    return H, matches[max_inliers]
