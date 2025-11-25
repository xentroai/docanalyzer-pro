#include <iostream>
#include <string>
#include <vector>
#include <filesystem>
#include <algorithm>
#include <cmath>

#include <poppler-document.h>
#include <poppler-page.h>
#include <tesseract/baseapi.h>
#include <leptonica/allheaders.h>
#include <nlohmann/json.hpp>
#include <opencv2/opencv.hpp>

using json = nlohmann::json;
using namespace std;
namespace fs = std::filesystem;

// --- DEBUG HELPER ---
void log(string msg) {
    cerr << "[CPP-DEBUG] " << msg << endl;
}

// --- VISION PIPELINE: THICKEN TEXT ---
string preprocess_image(string filepath) {
    log("Processing image: " + filepath);
    cv::Mat img = cv::imread(filepath);
    if (img.empty()) {
        log("ERROR: Could not read image file");
        return "";
    }

    // 1. Upscale (3x) - Keeps text shape
    cv::resize(img, img, cv::Size(), 3.0, 3.0, cv::INTER_CUBIC);

    // 2. Grayscale
    cv::Mat gray;
    if (img.channels() == 3) {
        cv::cvtColor(img, gray, cv::COLOR_BGR2GRAY);
    } else {
        gray = img;
    }

    // 3. ADAPTIVE THRESHOLD (Tuned for Receipts)
    // BlockSize=31 (Larger area to ignore paper texture)
    // C=15 (Higher contrast requirement to drop background noise)
    cv::Mat binary;
    cv::adaptiveThreshold(gray, binary, 255, 
                          cv::ADAPTIVE_THRESH_GAUSSIAN_C, 
                          cv::THRESH_BINARY, 31, 15);

    // 4. TEXT THICKENING (The Fix)
    // We 'erode' the white pixels, which makes the black text thicker.
    // This connects broken lines in thin fonts.
    cv::Mat kernel = cv::getStructuringElement(cv::MORPH_RECT, cv::Size(2, 2));
    cv::erode(binary, binary, kernel);

    string temp_path = "output/temp_processed.png";
    fs::create_directories("output");
    cv::imwrite(temp_path, binary);
    log("Saved preprocessed image to: " + temp_path);
    return temp_path;
}

// --- ROTATION HELPER ---
void rotate_90(string input_path, string output_path) {
    cv::Mat src = cv::imread(input_path);
    if (src.empty()) return;
    cv::Mat dst;
    cv::rotate(src, dst, cv::ROTATE_90_CLOCKWISE);
    cv::imwrite(output_path, dst);
}

// --- EXTRACTORS ---

string extract_pdf(string filepath) {
    string full_text = "";
    poppler::document* doc = poppler::document::load_from_file(filepath);
    if (!doc) return "";
    int pages = doc->pages();
    for (int i = 0; i < pages; ++i) {
        poppler::page* p = doc->create_page(i);
        if (p) {
            std::vector<char> bytes = p->text().to_utf8();
            full_text.append(bytes.begin(), bytes.end());
            full_text += "\n";
            delete p;
        }
    }
    delete doc;
    return full_text;
}

string run_tesseract(string image_path, int* confidence_out) {
    tesseract::TessBaseAPI* api = new tesseract::TessBaseAPI();
    if (api->Init(NULL, "eng")) { 
        log("ERROR: Tesseract Init failed.");
        return "";
    }
    
    // PSM 4 = Single Column (Great for receipts/invoices)
    // PSM 6 = Single Block (Also good)
    // We try 4 here as it handles lists well
    api->SetPageSegMode(tesseract::PSM_SINGLE_COLUMN);

    Pix* image = pixRead(image_path.c_str());
    if (!image) return "";

    api->SetImage(image);
    
    char* outText = api->GetUTF8Text();
    string result = "";
    if (outText) {
        result = string(outText);
        delete [] outText;
    }
    
    *confidence_out = api->MeanTextConf();
    
    api->End();
    delete api;
    pixDestroy(&image);
    return result;
}

string extract_image_ocr(string filepath, json &debug_info) {
    string current_image = preprocess_image(filepath);
    if (current_image == "") return "";
    
    string best_text = "";
    int best_conf = -1;
    string best_img = "";

    // ROTATION LOOP
    int rot_codes[] = {-1, 0, 1, 2}; // Just indices for tracking
    string rot_names[] = {"0_deg", "90_deg", "180_deg", "270_deg"};

    for (int i = 0; i < 4; i++) {
        // Save rotation step
        string current_rot_path = "output/debug_" + rot_names[i] + ".png";
        
        if (i == 0) {
            // 0 deg: Just copy base
            cv::Mat temp = cv::imread(current_image);
            cv::imwrite(current_rot_path, temp);
        } else {
            // Rotate previous result
            rotate_90(current_image, current_image); 
            cv::Mat temp = cv::imread(current_image);
            cv::imwrite(current_rot_path, temp);
        }

        int conf = 0;
        string text = run_tesseract(current_image, &conf);
        
        debug_info["rotations"][rot_names[i]]["path"] = current_rot_path;
        debug_info["rotations"][rot_names[i]]["conf"] = conf;

        // Logic: Prefer text with length AND confidence
        if (conf > best_conf && text.length() > 20) {
            best_conf = conf;
            best_text = text;
            best_img = current_rot_path;
        }
    }
    
    if (best_img != "") debug_info["best_image"] = best_img;
    else debug_info["best_image"] = "output/debug_0_deg.png"; // Default

    return best_text;
}

// --- MAIN ---
int main(int argc, char* argv[]) {
    if (argc < 2) return 1;
    string file_path = argv[1];
    
    if (!fs::exists(file_path)) {
        json err; err["status"] = "error"; 
        cout << err.dump(4) << endl; 
        return 1;
    }
    
    fs::create_directories("output");
    string extension = fs::path(file_path).extension().string();
    transform(extension.begin(), extension.end(), extension.begin(), ::tolower);

    string extracted_text = "";
    string method = "";
    json debug_info;

    try {
        if (extension == ".pdf") {
            method = "PDF_POPPLER";
            extracted_text = extract_pdf(file_path);
        } 
        else {
            method = "OCR_THICKENED";
            extracted_text = extract_image_ocr(file_path, debug_info);
        }
    } catch (...) { extracted_text = ""; }

    json output;
    output["status"] = "success";
    output["method"] = method;
    output["content"] = extracted_text;
    output["filepath"] = file_path;
    output["debug"] = debug_info;

    cout << output.dump(4) << endl;
    return 0;
}