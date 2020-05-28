pipeline {
	agent none
	stages {
		stage('scan-vulns') {
            when{
                branch 'dev'
            }

             agent any
	    //agent {
            //    docker { 
              //      image 'qualys/qcs-sensor:latest'
                //    reuseNode true
		  //  args '-v /var/run:/var/run'
                //}   
            //}
            steps {
                //notifyBuild(currentBuild.result)
		 withCredentials([
			 usernamePassword(credentialsId: 'mody-docker-credentials', passwordVariable: 'password', usernameVariable: 'username'),
			 usernamePassword(credentialsId: 'qualysSensorCred', passwordVariable: 'activationId', usernameVariable: 'customerId')
		 ]) {
		     sh 'docker run -d --restart on-failure -v /var/run:/var/run -v ~/qualys/data:/usr/local/qualys/qpa/data -e ACTIVATIONID=$activationId  -e CUSTOMERID=$customerId -e POD_URL=https://cmsqagpublic.qg2.apps.qualys.eu/ContainerSensor  --net=host  --name qualys-container-sensor qualys/qcs-sensor:latest'
		  }
                    sh 'make build_image_dev'
		
		    sh 'docker images'
		script {
			  def IMAGE_ID = sh(script: "docker images | grep -E '^beopenit/onboarding-api-dev' | head -1 | awk '{print \$3}'", returnStdout:true).trim()
		          	env.IMAGE_ID = IMAGE_ID
				//env.IMAGE_ID = '5db2183224612e43a7ff1dfedbefa60113963f629b55dcc62b2b3c2db1d01837'
			}

		 getImageVulnsFromQualys useGlobalConfig:true, imageIds: env.IMAGE_ID
		 //sh 'docker login -u $username -p $password'
		 //sh 'make push_image_dev'
	    } 
	    
		    	
	}
		//stage('deploy-dev-env') {
		//	agent any
		//	when {
		//		branch 'dev'
		//	}
		//	steps {
		//		withCredentials([usernamePassword(credentialsId: 'openshift_dakario_credentials', passwordVariable: 'password', usernameVariable: 'username')]) {
		//			sh 'oc login -u $username -p $password ${OPENSHIFT_ENV_URL_DEV} --insecure-skip-tls-verify'
		//		}
		//		withCredentials([file(credentialsId: 'onboarding_api_secrets_dev', variable: 'secretfile')]) {
		//			withCredentials([file(credentialsId: 'onboarding_api_kub_config_dev', variable: 'kub_config')]) {
		//				sh 'make SECRET_FILE=$secretfile KUB_CONFIG=kub_config deploy_openshift_dev'
		//			}
		//		}
		//	}
		//}

		//stage('build-and-push-docker-image-master') {
		//	agent any
		//	when{
		//		branch 'master'
		//	}
		//	steps {
		//		withCredentials([usernamePassword(credentialsId: 'mody-docker-credentials', passwordVariable: 'password', usernameVariable: 'username')]) {
		//			sh 'docker login -u $username -p $password'
		//		}
		//		sh 'make build_image_prod'
		//		sh 'make push_image_prod'
		//	}
		//}
		//stage('deploy-prod-env') {
		//	agent any
		//	when {
		//		branch 'master'
		//	}
		//	steps {
		//		withCredentials([usernamePassword(credentialsId: 'openshift_dakario_credentials', passwordVariable: 'password', usernameVariable: 'username')]) {
		//			sh 'oc login -u $username -p $password ${OPENSHIFT_ENV_URL_PROD} --insecure-skip-tls-verify'
		//		}
		//		withCredentials([file(credentialsId: 'onboarding_api_secrets_prod', variable: 'secretfile')]) {
		//		   withCredentials([file(credentialsId: 'onboarding_api_kub_config_dev', variable: 'kub_config')]) {
		//				sh 'make SECRET_FILE=$secretfile KUB_CONFIG=kub_config deploy_openshift_prod'
		//			}
		//		}
		//	}
		//}
	}

	/**post {
		success {
			slackSend channel: '#test-notif-jenkins',
			color: 'good',
			message: "The pipeline ${currentBuild.fullDisplayName} completed successfully."
		}
	}**/
}
