.PHONY: package deploy clean

package:
	rm -rf build
	pip install -r requirements.txt -t build/
	cp -r app build/app
	cp -r handlers build/handlers
	cp -r templates build/templates

deploy: package
	cd terraform && terraform apply

clean:
	rm -rf build lambda.zip
