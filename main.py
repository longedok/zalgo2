from zalgo.Application import Application

if __name__ == '__main__':
    import sys

    app = Application(sys.argv)
    sys.exit(app.exec_())
