VERSION=0.0.1
TAG ?= $(shell git log -1 --format=%h)
IMAGE=onboarding_api
ORG=beopenit
CURRENTDIR ?= $(shell pwd)

APP_VERSION = "v.$(VERSION).${TAG}"
APP_NAME = "onboarding-api"
ORGANISATION_NAME = "beopenit"
OPENSHIFT_PROJECT_NAME = "onboarding"
OPENSHIFT_PROJECT_NAME_DEV = "onboarding-dev"
OPENSHIFT_ENV_URL_PROD = "https://console.cloud.dakar.io"
OPENSHIFT_ENV_URL_DEV = "https://console.cloud.dakar.io"
OPENSHIFT_SECRET_NAME_PROD = "secrets-conf"
OPENSHIFT_SECRET_NAME_DEV = "secrets-conf"

APP_NAME_DEV = "${APP_NAME}-dev"
IMAGE_NAME = "${ORGANISATION_NAME}/${APP_NAME}"
IMAGE_NAME_DEV = "${ORGANISATION_NAME}/${APP_NAME_DEV}"
IMAGE_FULL_NAME = "${IMAGE_NAME}:${APP_VERSION}"
IMAGE_FULL_NAME_DEV = "${IMAGE_NAME_DEV}:${APP_VERSION}"


lint:
	@${EXEC} python3 -m flake8 --statistics --max-line-length=150 --exclude=venv || true

build_image_prod:
	@echo "Build docker image prod"
	docker build -t ${IMAGE_FULL_NAME} -f Dockerfile .
	docker tag ${IMAGE_FULL_NAME} ${IMAGE_NAME}:latest
build_image_dev:
	@echo "Build docker image dev"
	docker build -t ${IMAGE_FULL_NAME_DEV} -f Dockerfile .
	docker tag ${IMAGE_FULL_NAME_DEV} ${IMAGE_NAME_DEV}:latest

push_image_prod:
	@echo "Push docker image prod"
	docker push ${IMAGE_FULL_NAME}
	docker push ${IMAGE_NAME}:latest
	docker rmi -f ${IMAGE_FULL_NAME} || true
	docker rmi -f ${IMAGE_NAME}:latest || true
	docker rmi -f $(docker images -q --filter "dangling=true") || true
push_image_dev:
	@echo "Push docker image dev"
	docker push ${IMAGE_FULL_NAME_DEV}
	docker push ${IMAGE_NAME_DEV}:latest
	docker rmi -f ${IMAGE_FULL_NAME_DEV} || true
	docker rmi -f ${IMAGE_NAME_DEV}:latest || true
	docker rmi -f $(docker images -q --filter "dangling=true") || true

deploy_openshift_prod:
	@echo "Deploy to openshift prod env"
	oc new-project ${OPENSHIFT_PROJECT_NAME} || true
	oc create -f ${SECRET_FILE} || true
	(\
		oc new-app ${IMAGE_FULL_NAME} -n ${OPENSHIFT_PROJECT_NAME} &&\
		oc set env dc/${APP_NAME} --from=secret/${OPENSHIFT_SECRET_NAME_PROD} -n ${OPENSHIFT_PROJECT_NAME} &&\
		oc expose service/${APP_NAME} -n ${OPENSHIFT_PROJECT_NAME} \
	)\
		|| (\
			oc set triggers dc/${APP_NAME} --remove-all -n ${OPENSHIFT_PROJECT_NAME} &&\
			oc set triggers dc/${APP_NAME} --from-image=${APP_NAME}:${APP_VERSION} -c ${APP_NAME} -n ${OPENSHIFT_PROJECT_NAME} &&\
			oc import-image is/${APP_NAME}:${APP_VERSION} --from ${IMAGE_FULL_NAME} -n ${OPENSHIFT_PROJECT_NAME}\
		)
deploy_openshift_dev:
	@echo "Deploy to openshift prod env"
	oc new-project ${OPENSHIFT_PROJECT_NAME_DEV} || true
	oc create -f ${SECRET_FILE} || true
	oc create configmap kube-config-dev --from-file=${KUB_CONFIG} -n ${OPENSHIFT_PROJECT_NAME_DEV} || true
	(\
		oc new-app ${IMAGE_FULL_NAME_DEV} -n ${OPENSHIFT_PROJECT_NAME_DEV} &&\
		oc set env dc/${APP_NAME_DEV} --from=secret/${OPENSHIFT_SECRET_NAME_DEV} -n ${OPENSHIFT_PROJECT_NAME_DEV} &&\
		oc expose service/${APP_NAME_DEV} -n ${OPENSHIFT_PROJECT_NAME_DEV} \
	)\
		|| (\
				oc set triggers dc/${APP_NAME_DEV} --remove-all -n ${OPENSHIFT_PROJECT_NAME_DEV} &&\
				oc set triggers dc/${APP_NAME_DEV} --from-image=${APP_NAME_DEV}:${APP_VERSION} -c ${APP_NAME_DEV} -n ${OPENSHIFT_PROJECT_NAME_DEV} &&\
				oc import-image is/${APP_NAME_DEV}:${APP_VERSION} --from ${IMAGE_FULL_NAME_DEV} -n ${OPENSHIFT_PROJECT_NAME_DEV} \
			)

deploy_local_dev: build_image_dev
	docker run --rm --name ${APP_NAME} -p 8080:80 -v ${CURRENTDIR}:/app -w /app \
	-e MAIL_SERVER=${MAIL_SERVER} \
	-e MAIL_PORT=${MAIL_PORT} \
	-e MAIL_USERNAME=${MAIL_USERNAME} \
	-e MAIL_PASSWORD=${MAIL_PASSWORD} \
	${IMAGE_NAME_DEV}:latest 
deploy_local_prod: build_image_prod
	docker run --rm --name ${APP_NAME} -p 8080:80 -v ${CURRENTDIR}:/app -w /app \
	-e MAIL_SERVER=${MAIL_SERVER} \
	-e MAIL_PORT=${MAIL_PORT} \
	-e MAIL_USERNAME=${MAIL_USERNAME} \
	-e MAIL_PASSWORD=${MAIL_PASSWORD} \
	${IMAGE_NAME}:latest

