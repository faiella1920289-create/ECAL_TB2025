void fileCheck(const char* filename, const char* objname) {
    TFile *f = TFile::Open(filename);
    if (!f || f->IsZombie()) {
        std::cout << "FILE_ZOMBIE" << std::endl;
        return;
    }
    if (f->Get(objname)) {
        std::cout << "FILE_OK" << std::endl;
    } else {
        std::cout << "FILE_NOT_FOUND" << std::endl;
    }
    f->Close();
}
